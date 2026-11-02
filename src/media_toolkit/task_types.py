from dataclasses import dataclass, field
from enum import Enum, auto
from time import monotonic

@dataclass(slots=True, frozen=True)
class EstimProgressState:
    current: float | None
    total: float | None
    speed: float | None


@dataclass(slots=True, frozen=True)
class ProgressState:
    current: float | None
    total: float | None
    speed: float | None
    last_updt: float = field(default_factory=monotonic)

    def estim_progress(self) -> EstimProgressState:
        """estimated current progress from object init and current time"""

        if (self.speed is None or
            self.current is None or
            self.total is None):
            return EstimProgressState(self.current, self.total, self.speed)

        curr_time = monotonic()
        time_gap = curr_time - self.last_updt
        estim_bytes = self.current + self.speed * time_gap
        return EstimProgressState(min(estim_bytes, self.total), self.total, self.speed)


class DownloadState(Enum):
    INIT = auto()
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
