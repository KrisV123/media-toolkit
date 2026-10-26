from textual.app import App
from textual.events import Mount
from textual.widgets import Header, Footer, Static, Input, Button, Select, Label
from textual.widget import Widget
from textual.containers import ScrollableContainer
from textual.types import NoSelection

from collections.abc import Iterable
from urllib.parse import urlsplit

from yt_convertor.type import AUDIO_FORMATS, VIDEO_FORMATS, DownloadInfo
from yt_convertor.backend.services.audio_downloader import AudioDownloaderTask
from yt_convertor.backend.services.video_downloader import VideoDownloaderTask
from yt_convertor.backend import TaskManager
from yt_convertor.backend import Task

from .download_single import DownloadSingleWidget
from .download_playlist import DownloadPlaylistWidget
from .messages import Restart

import logging
LOGGER = logging.getLogger(__name__)

class UIException(Exception):
    pass


class InputFormats(Static):
    def compose(self) -> Iterable[Widget]:
        yield Button(label='MP3', id='mp3')
        yield Button(label='MP4', id='mp4')
        yield Button(label='FLAC', id='flac')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        for button in self.query(Button):
            button.remove_class('SelectedButton')

        button = event.button
        button.add_class('SelectedButton')

    def get_selected_format(self) -> str:
        for button in self.query(Button):
            if button.has_class('SelectedButton'):
                assert button.id is not None
                return button.id
        return ""


class ExtraInputSettings(Static):
    audio_quality = [
        "128 kbps", "160 kbps", "192 kbps", "224 kbps", "256 kbps", "320 kbps"
    ]
    video_quality = [
        "480p", "720p", "1080p", "1440p", "2160p"
    ]

    def compose(self) -> Iterable[Widget]:
        yield Select[str](
            options=[
                (quality , quality)
                for quality in self.audio_quality
            ],
            prompt='audio quality',
            id='audio_quality'
        )
        yield Select[str](
            options=[(quality, quality) for quality in self.video_quality],
            prompt='video quality',
            id='video_quality'
        )
        yield Button(label='PLAYLIST', id='playlist')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        if button.has_class('SelectedButton'):
            button.remove_class('SelectedButton')
        else:
            button.add_class('SelectedButton')

    def is_playlist(self) -> bool:
        button = self.query_one('#playlist', Button)
        return button.has_class('SelectedButton')

    def get_audio_quality(self) -> str:
        select = self.query_one('#audio_quality', Select)
        value = select.value
        return self.audio_quality[-1] if isinstance(value, NoSelection) else value

    def get_video_quality(self) -> str:
        select = self.query_one('#video_quality', Select)
        value = select.value
        return self.video_quality[-1] if isinstance(value, NoSelection) else value


class InputEntry(Static):
    def compose(self) -> Iterable[Widget]:
        yield Input(placeholder="add URL", id="url_input")
        yield Button(label="convert", id="url_enter")

    def get_url_adress(self) -> str:
        return self.query_one("#url_input", Input).value

    def reset_url_adress(self) -> None:
        input_widget = self.query_one("#url_input", Input)
        input_widget.value = ""

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        button.disabled = True
        input_bar = self.app.query_one(InputBar)
        main_frame = self.app.query_one(MainFrame)
        await main_frame.add_download_widget(input_bar.get_download_info())
        self.reset_url_adress()
        button.disabled = False


class InputBar(Static):
    def compose(self) -> Iterable[Widget]:
        yield InputEntry()
        yield InputFormats()
        yield ExtraInputSettings()

    def get_download_info(self) -> DownloadInfo:
        input_entry = self.query_one(InputEntry)
        input_formats = self.query_one(InputFormats)
        extra_input_settings = self.query_one(ExtraInputSettings)
        return DownloadInfo(
            link=input_entry.get_url_adress(),
            widget_name=input_entry.get_url_adress(),
            format=input_formats.get_selected_format(),
            is_playlist=extra_input_settings.is_playlist(),
            audio_quality=extra_input_settings.get_audio_quality(),
            video_quality=extra_input_settings.get_video_quality()
        )


class ErrorWidget(Static):
    def __init__(self, msg: str):
        super().__init__()
        self.msg = msg

    def compose(self) -> Iterable[Widget]:
        yield Label(content=self.msg)

    def _on_mount(self, event: Mount) -> None:
        self.border_title = "Input Error"


class MainFrame(Static):

    def compose(self) -> Iterable[Widget]:
        yield ScrollableContainer(id="downloads")
        yield InputBar()

    async def add_download_widget(self, download_info: DownloadInfo) -> None:
        downloads_widget = self.query_one("#downloads")

        validation_msg = self.get_validation_error_msg(download_info)
        if validation_msg:
            downloads_widget.mount(ErrorWidget(validation_msg))
            return

        manager = TaskManager()
        """
        widget = DownloadPlaylistWidget if download_info.is_playlist else DownloadSingleWidget
        format = download_info.format
        task: type[Task]
        if format in AUDIO_FORMATS:
            task = AudioDownloaderTask
        elif format in VIDEO_FORMATS:
            task = VideoDownloaderTask
        else:
            raise UIException("service for current format does not exist or is not registered")

        regist_task = await manager.register(task, download_info)
        downloads_widget.mount(widget(download_info, regist_task))
        """

        widget = DownloadPlaylistWidget if download_info.is_playlist else DownloadSingleWidget
        format = download_info.format

        if format in AUDIO_FORMATS:
            audio_task = await manager.register(AudioDownloaderTask, download_info)
            downloads_widget.mount(widget(download_info, audio_task))
        elif format in VIDEO_FORMATS:
            video_task = await manager.register(VideoDownloaderTask, download_info)
            downloads_widget.mount(widget(download_info, video_task))
        else:
            raise UIException("service for current format does not exist or is not registered")

        downloads_widget.scroll_end()

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
            raise UIException("service for current format does not exist or is not registered")
        elif download_info.audio_quality == "":
            return "Audio quality is missing"
        elif download_info.format in VIDEO_FORMATS and download_info.video_quality == "":
            return "For video format, video quality have to be selected"

        return None

    async def on_restart(self, message: Restart):
        LOGGER.debug('Restart message recived')
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
