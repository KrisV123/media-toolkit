from textual import events
from textual.widgets import Static, Input, Button, Select
from textual.widget import Widget
from textual.types import NoSelection
from textual.binding import Binding

from collections.abc import Iterable

from media_toolkit.type import DownloadInfo
from .messages import ConvertRequested

class InputFormats(Static):
    BINDINGS = [
        ('left', 'left', 'Left'),
        ('right', 'right', 'Right')
    ]

    def __init__(self):
        super().__init__()
        self.cursor = 0

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

    def on_descendant_focus(self, event: events.DescendantFocus):
        widget = event.widget
        if isinstance(widget, Button):
            items = list(self.query(Button))
            self.cursor = items.index(widget)

    def _move(self, step: int) -> None:
        items = list(self.query(Button))
        if not items:
            return
        self.cursor = max(0, min(self.cursor + step, len(items) - 1))
        items[self.cursor].focus()

    def action_left(self) -> None:
        self._move(-1)

    def action_right(self) -> None:
        self._move(+1)


class QualitySelect[T](Select[T], inherit_bindings=False):
    BINDINGS = [
        Binding("enter", "show_overlay", "Show menu", show=False),
    ]


class ExtraInputSettings(Static):
    BINDINGS = [
        ('left', 'left', 'Left'),
        ('right', 'right', 'Right')
    ]

    audio_quality = [
        "32 kbps", "48 kbps", "64 kbps", "80 kbps",
        "96 kbps", "112 kbps", "128 kbps", "160 kbps",
        "192 kbps", "224 kbps", "256 kbps", "320 kbps",
    ]
    video_quality = ["480p", "720p", "1080p", "1440p", "2160p"]

    def __init__(self):
        super().__init__()
        self.cursor = 0

    def compose(self) -> Iterable[Widget]:
        yield QualitySelect[str](
            options=[
                (quality , quality)
                for quality in self.audio_quality
            ],
            prompt='audio quality',
            id='audio_quality'
        )
        yield QualitySelect[str](
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

    def on_descendant_focus(self, event: events.DescendantFocus):
        widget = event.widget
        if isinstance(widget, Select | Button):
            items = list(self.query("Select, Button"))
            self.cursor = items.index(widget)

    def _move(self, step: int) -> None:
        items = list(self.query("Select, Button"))
        if not items:
            return
        self.cursor = max(0, min(self.cursor + step, len(items) - 1))
        items[self.cursor].focus()

    def action_left(self) -> None:
        self._move(-1)

    def action_right(self) -> None:
        self._move(+1)


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
        self.post_message(ConvertRequested())
        button.disabled = False


class InputBar(Static):
    can_focus = True

    def __init__(self):
        super().__init__()
        self.cursor = 0

    BINDINGS = [
        Binding('up', 'up', 'Up'),
        Binding('down', 'down', 'Down'),
        Binding('space', 'convert', 'Convert', priority=True)
    ]

    def compose(self) -> Iterable[Widget]:
        self._groups: list[Widget] = [InputEntry(), InputFormats(), ExtraInputSettings()]
        yield from self._groups

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

    def action_convert(self) -> None:
        convert_button = self.query_one('#url_enter', Button)
        convert_button.press()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.action_convert()

    def on_descendant_focus(self, event: events.DescendantFocus):
        widget = event.widget
        for index, group in enumerate(self._groups):
            if widget in group.ancestors:
                self.cursor = index
                break

    def _move(self, step: int) -> None:
        groups = self._groups
        self.cursor = max(0, min(self.cursor + step, len(groups) - 1))
        groups[self.cursor].query("Input, Select, Button").first().focus()

    def action_up(self) -> None:
        self._move(-1)

    def action_down(self) -> None:
        self._move(+1)
