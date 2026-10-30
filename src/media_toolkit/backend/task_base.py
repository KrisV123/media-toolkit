from abc import ABC, abstractmethod
from media_toolkit.backend.event_bus import EventBus

from media_toolkit.type import DownloadInfo
from media_toolkit.task_types import TaskState, ProgressState

class TaskError(Exception):
    pass


class Task(ABC):

    def __init__(self, downlaod_info: DownloadInfo, id: int):
        self._download_info = downlaod_info
        self._id = id
        self._event_bus = EventBus()

    @property
    def download_info(self) -> DownloadInfo:
        return self._download_info

    @property
    def id(self) -> int:
        return self._id

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @abstractmethod
    def setup(self) -> bool:
        """
        routine, that correctly setup task.
        Returns True, if it was success and False if not
        """

    @property
    @abstractmethod
    def fail(self) -> Exception | None:
        """returns exception if task failed, otherwise return None"""

    @property
    @abstractmethod
    def status(self) -> TaskState:
        """returns state of the task"""

    @abstractmethod
    def start(self) -> None:
        """start task routine"""

    @abstractmethod
    def get_metadata(self) -> None:
        """load metadata about object"""

    @abstractmethod
    def stop(self) -> None:
        """stop task routine"""

    @abstractmethod
    def prepare_resume(self) -> None:
        """prepare task after pause"""

    @abstractmethod
    def cancel(self) -> None:
        """clean garbage left behind (temporary files), reset states, ect."""

    @abstractmethod
    def progress(self) -> ProgressState:
        """return current progress state of whole service workload"""
