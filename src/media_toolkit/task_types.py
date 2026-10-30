from dataclasses import dataclass
from enum import Enum, auto

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
