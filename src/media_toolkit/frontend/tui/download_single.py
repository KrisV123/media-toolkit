from textual.widgets import Static, Label
from textual.widget import Widget

from media_toolkit.task_types import TaskState

from media_toolkit.backend import Events

from .download_helpers import DownloadLabels, Progress, ICONS
from .messages import Changed
from ...protocols import TaskSupportBasics

from collections.abc import Iterable

class DownloadSingleWidget(Static):
    def __init__(self, backend_task: TaskSupportBasics):
        super().__init__()
        download_info = backend_task.download_info
        self.format = download_info.format
        self.audio_quality = download_info.audio_quality
        self.video_quality = download_info.video_quality
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield DownloadLabels(self.backend_task)
        yield Progress(self.backend_task)

    def on_mount(self) -> None:
        self.border_title = f'{ICONS[self.backend_task.status]}  {self.backend_task.title}'
        self.border_subtitle = str(self.backend_task.id)
        meta_event = Events.CHANGED_META
        self.backend_task.event_bus.subscribe(meta_event, self.update_border_title)
        status_event = Events.UPDATE_TASK_STATUS
        self.backend_task.event_bus.subscribe(status_event, self.update_border_title)

    def update_border_title(self) -> None:
        current_state_emoji = ICONS[self.backend_task.status]
        self.border_title = f'{current_state_emoji}  {self.backend_task.title}'

    def on_changed(self, messege: Changed) -> None:
        status = messege.status
        if status == TaskState.FAIL:
            self.mount(Label(f'{str(self.backend_task.fail)}'))

        if status in (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED):
            download_labels = self.query_one(DownloadLabels)
            download_labels.update_fallback()
