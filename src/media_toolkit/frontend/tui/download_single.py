from textual.widgets import Label

from media_toolkit.task_types import TaskState
from media_toolkit.protocols import TaskSupportBasics

from .download_helpers import DownloadLabels, DownloadItem
from .messages import TaskStatusChanged


class DownloadSingleWidget(DownloadItem[TaskSupportBasics]):
    def on_task_status_changed(self, messege: TaskStatusChanged) -> None:
        status = self.backend_task.status
        if status == TaskState.FAIL:
            self.mount(Label(f'{str(self.backend_task.fail)}'))

        if status in (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED):
            download_labels = self.query_one(DownloadLabels)
            download_labels.update_fallback()
