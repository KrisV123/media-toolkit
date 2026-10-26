from textual.widgets import Static, Label
from textual.widget import Widget

from yt_convertor.type import DownloadInfo
from yt_convertor.backend import Task, TaskState, TaskManager, Events

from .download_helpers import DownloadLabels, Progress, ICONS
from .messages import Changed

from collections.abc import Iterable

class DownloadSingleWidget(Static):
    def __init__(self, download_info: DownloadInfo, backend_task: Task):
        super().__init__()
        self.format = download_info.format
        self.audio_quality = download_info.audio_quality
        self.video_quality = download_info.video_quality
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield DownloadLabels(self.format, self.audio_quality, self.video_quality)
        yield Progress(self.backend_task)

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
