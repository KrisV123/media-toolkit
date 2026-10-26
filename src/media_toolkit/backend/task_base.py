from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
from media_toolkit.backend.event_bus import EventBus

from media_toolkit.type import DownloadInfo

class TaskError(Exception):
    pass


@dataclass(slots=True, frozen=True)
class ProgressState:
    current: float | None
    total: float | None


class DownloadState(Enum):
    DOWNLOADING = auto()
    FINISHED = auto()
    ERROR = auto()


class TaskState(Enum):
    NOT_READY = auto()
    READY = auto()
    IN_PROCESS = auto()
    FINISHED = auto()
    FAIL = auto()
    PAUSED = auto()
    CANCELLED = auto()


class Task(ABC):

    def __init__(self, downlaod_info: DownloadInfo, id: int):
        self.download_info = downlaod_info
        self.id = id
        self._event_bus = EventBus()

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    @abstractmethod
    def title(self) -> str:
        """returns widget name"""

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
