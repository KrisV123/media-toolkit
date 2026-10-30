from textual.message import Message
from media_toolkit.task_types import TaskState
from media_toolkit.type import DownloadInfo

class Changed(Message):
    def __init__(self, status: TaskState):
        super().__init__()
        self.status = status


class Restart(Message):
    def __init__(self, download_info: DownloadInfo):
        super().__init__()
        self.download_info = download_info
