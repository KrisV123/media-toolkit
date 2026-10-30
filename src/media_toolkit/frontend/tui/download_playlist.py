from textual.events import Mount
from textual.widgets import Static, Label
from textual.widget import Widget

from collections.abc import Iterable

from media_toolkit.backend import TaskManager, Events
from media_toolkit.protocols import TaskSupportsCollection
from media_toolkit.task_types import TaskState, DownloadState

from .download_helpers import DownloadLabels, Progress, ICONS
from .messages import Changed

SOLO_ICONS = {
    DownloadState.DOWNLOADING: '⌛',
    DownloadState.FINISHED: '✔ ',
    DownloadState.ERROR: '❌'
}

class PlaylistSingleVideo(Static):

    def __init__(self, video_name: str | None, backend_task: TaskSupportsCollection, ord: int):
        super().__init__()
        self.video_name = video_name
        self.backend_task = backend_task
        self.ord = ord

    def compose(self) -> Iterable[Widget]:
        yield Label(content=SOLO_ICONS[DownloadState.DOWNLOADING], id="icon")
        yield Label(content="   ")
        yield Label(content=f"  0 %", id="percentage")
        yield Label(content="  ")
        yield Label(content=f"{self.video_name}")
        yield Label(content="", id='fallback-label')

    def _on_mount(self, event: Mount) -> None:
        self._percentage = self.query_one("#percentage", Label)
        self._icon = self.query_one('#icon', Label)
        self._fallback = self.query_one('#fallback-label', Label)
        self._timer = self.set_interval(0.3, self.update_percentage)

    def update_percentage(self) -> None:
        if self.backend_task.playlist_ord == self.ord:
            progress, status = self.backend_task.current_video_progress()
            if progress.total is not None and progress.current:
                progress_num = int((progress.current / progress.total) * 100)
                self._icon.update(content=SOLO_ICONS[status])
                self._percentage.update(content=f'{progress_num:3d} %')
            if status == DownloadState.FINISHED:
                self.update_fallback()

        task_status = self.backend_task.status
        if task_status in (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED):
            self._timer.stop()

    def update_fallback(self) -> None:
        fallback = self.backend_task.check_fallback(self.ord)
        if not fallback:
            return
        miss_flags = ', '.join(miss for miss in fallback)
        self._fallback.update(content="   ↪ " + miss_flags)


class PlaylistCatalog(Static):
    def __init__(self, backend_task: TaskSupportsCollection):
        super().__init__()
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield from ()

    def _on_mount(self, event: Mount) -> None:
        if len(self.backend_task.playlist_items) == 0:
            meta_event = Events.CHANGED_META
            TaskManager().event_bus.subscribe(meta_event, self.load_single_videos)
        else:
            self.load_single_videos()

    def load_single_videos(self) -> None:
        for ord, title in enumerate(self.backend_task.playlist_items):
            self.mount(PlaylistSingleVideo(title, self.backend_task, ord + 1))
        meta_event = Events.CHANGED_META
        TaskManager().event_bus.unsubsrcribe(meta_event, self.load_single_videos)


class DownloadPlaylistWidget(Static):
    def __init__(self, backend_task: TaskSupportsCollection):
        super().__init__()
        download_info = backend_task.download_info
        self.format = download_info.format
        self.audio_quality = download_info.audio_quality
        self.video_quality = download_info.video_quality
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield DownloadLabels(self.backend_task)
        yield Progress(self.backend_task)
        yield PlaylistCatalog(self.backend_task)

    def on_mount(self) -> None:
        self.border_title = f'{ICONS[self.backend_task.status]}  {self.backend_task.title}'
        self.border_subtitle = str(self.backend_task.id)
        meta_event = Events.CHANGED_META
        TaskManager().event_bus.subscribe(meta_event, self.update_border_title)
        status_event = Events.UPDATE_TASK_STATUS
        self.backend_task.event_bus.subscribe(status_event, self.update_border_title)

    def update_border_title(self) -> None:
        current_state_emoji = ICONS[self.backend_task.status]
        self.border_title = f'{current_state_emoji}  {self.backend_task.title}'

    def on_changed(self, messege: Changed) -> None:
        status = messege.status
        if status == TaskState.FAIL:
            self.mount(Label(f'{str(self.backend_task.fail)}'))
