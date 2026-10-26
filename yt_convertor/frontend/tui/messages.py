from textual.message import Message
from yt_convertor.backend import TaskState
from yt_convertor.type import DownloadInfo

class Changed(Message):
    def __init__(self, status: TaskState):
        super().__init__()
        self.status = status


class Restart(Message):
    def __init__(self, download_info: DownloadInfo):
        super().__init__()
        self.download_info = download_info
