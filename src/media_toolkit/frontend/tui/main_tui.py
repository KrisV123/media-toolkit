from textual import events
from textual.app import App
from textual.events import Mount
from textual.widgets import Header, Footer, Static, Button, Label
from textual.widget import Widget
from textual.containers import ScrollableContainer
from textual.binding import Binding

from collections.abc import Iterable
from urllib.parse import urlsplit

from media_toolkit.type import AUDIO_FORMATS, VIDEO_FORMATS, DownloadInfo

from media_toolkit.backend.services.audio_downloader import AudioDownloaderTask
from media_toolkit.backend.services.video_downloader import VideoDownloaderTask
from media_toolkit.backend import TaskManager

from .download_single import DownloadSingleWidget
from .download_playlist import DownloadPlaylistWidget
from .download_helpers import DownloadItem
from .input import InputBar, InputEntry
from .messages import Restart, ConvertRequested

class UIException(Exception):
    pass


class ErrorWidget(Static):
    def __init__(self, msg: str):
        super().__init__()
        self.msg = msg

    def compose(self) -> Iterable[Widget]:
        yield Label(content=self.msg)

    def _on_mount(self, event: Mount) -> None:
        self.border_title = "Input Error"


class DownloadsScrollable(ScrollableContainer):
    BINDINGS = [
        Binding("up", "focus_previous", "Previous"),
        Binding("down", "focus_next", "Next"),
    ]

    cursor = 0

    def on_descendant_focus(self, event: events.DescendantFocus):
        widget = event.widget
        if isinstance(widget, DownloadItem):
            itmes = list(self.query(DownloadItem))
            self.cursor = itmes.index(widget)

    def _move(self, step: int) -> None:
        items = list(self.query(DownloadItem))
        if not items:
            return
        self.cursor = max(0, min(self.cursor + step, len(items) - 1))
        items[self.cursor].focus()

    def action_focus_previous(self) -> None:
        self._move(-1)

    def action_focus_next(self) -> None:
        self._move(+1)


class MainFrame(Static):
    BINDINGS = [
        ('c', 'change_focus', 'Downloads/Input')
    ]

    def __init__(self) -> None:
        super().__init__()
        self.downloads_widget = DownloadsScrollable(id="downloads")
        self.input_bar = InputBar()

    def compose(self) -> Iterable[Widget]:
        yield self.downloads_widget
        yield self.input_bar

    def action_change_focus(self):
        focused_widget = self.app.focused

        if focused_widget is None:
            self.input_bar.focus()
        elif (focused_widget is self.downloads_widget or
              self.downloads_widget in focused_widget.ancestors):
            self.input_bar.focus()
        elif (focused_widget is self.input_bar or
              self.input_bar in focused_widget.ancestors):
            self.downloads_widget.focus()
        else:
            self.input_bar.focus()

    async def on_convert_requested(self, messege: ConvertRequested) -> None:
        input_bar = self.query_one(InputBar)
        download_info = input_bar.get_download_info()
        input_entry = self.query_one(InputEntry)
        input_entry.reset_url_adress()
        await self.add_download_widget(download_info)

    async def add_download_widget(self, download_info: DownloadInfo) -> None:
        validation_msg = self.get_validation_error_msg(download_info)
        if validation_msg:
            self.downloads_widget.mount(ErrorWidget(validation_msg))
            self.downloads_widget.scroll_end()
            return

        manager = TaskManager()
        widget = DownloadPlaylistWidget if download_info.is_playlist else DownloadSingleWidget
        format = download_info.format

        if format in AUDIO_FORMATS:
            audio_task = await manager.register(AudioDownloaderTask, download_info)
            self.downloads_widget.mount(widget(audio_task))
        elif format in VIDEO_FORMATS:
            video_task = await manager.register(VideoDownloaderTask, download_info)
            self.downloads_widget.mount(widget(video_task))
        else:
            raise UIException("service for current format does not exist or is not registered")

        self.downloads_widget.scroll_end()

    def is_url(self, url: str) -> bool:
        try:
            parsed = urlsplit(url)
            return (
                parsed.scheme in ('http', 'https') and
                bool(parsed.hostname)
            )
        except:
            return False

    def get_validation_error_msg(self, download_info: DownloadInfo) -> str | None:
        if download_info.link == "":
            return "Missing ulr link"
        elif not self.is_url(download_info.link):
            return "url link is not valid"
        elif download_info.widget_name == "":
            raise UIException("Missing widget name")
        elif download_info.format not in AUDIO_FORMATS | VIDEO_FORMATS:
            if download_info.format == "":
                return "Format is not selected"
            else:
                return "service for current format does not exist or is not registered"
        elif download_info.format == "":
            return "Format is not selected"
        elif download_info.format in VIDEO_FORMATS and download_info.video_quality == "":
            return "For video format, video quality have to be selected"
        elif download_info.audio_quality == "":
            return "Audio quality is missing"

        return None

    async def on_restart(self, message: Restart):
        await self.add_download_widget(message.download_info)


class YtConvertorApp(App):
    CSS_PATH = [
        '../css/global.css',
        '../css/input_bar.css',
        '../css/download_widgets.css'
    ]

    def compose(self) -> Iterable[Widget]:
        yield Header()
        yield MainFrame()
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#url_enter', Button).focus()
