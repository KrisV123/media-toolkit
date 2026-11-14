import shutil
import gc
from typing import Any, overload, Literal

from media_toolkit.type import DownloadInfo
from media_toolkit.protocols import TaskSupportsCollection
from media_toolkit.task_types import TaskState, DownloadState, ProgressState, EstimProgressState

from media_toolkit.backend import Task, TaskError
from media_toolkit.backend.event_bus import Events
from media_toolkit.backend.task_base import Task, TaskState, TaskError
from media_toolkit.backend.services.type import StoppedService

from .service import YoutubeBase

import logging
LOGGER = logging.getLogger(__name__)

class YoutubeBaseTask[ServiceT: YoutubeBase](Task, TaskSupportsCollection):
    def __init__(self, download_info: DownloadInfo, id: int, service: type[ServiceT]):
        super().__init__(download_info, id)
        self._service = service(download_info, id)
        self._exception: Exception | None = None
        self._change_status(TaskState.NOT_READY)
        self._setupped = False
        self._title: str = "..."
        self._playlist_items: list[str | None] = []
        self._metadata: dict[str, Any] | None = None
        self._meta_exception: Exception | None = None

        self._progress = (ProgressState(None, None, None), DownloadState.INIT)

        progress_event = Events.UPDATED_PROGRESS
        service_event_bus = self._service.event_bus
        service_event_bus.subscribe(progress_event, self.progress_event)

    def progress_event(self) -> None:
        self._progress = self._video_progress_state(self._service.progress_dict)

    @property
    def title(self) -> str:
        return self._title

    @property
    def fail(self) -> Exception | None:
        return self._exception

    @property
    def status(self) -> TaskState:
        return self._state

    def _change_status(self, value: TaskState) -> None:
        """internal method. Status shoud not be mutated manually"""

        self._state = value
        event = Events.UPDATE_TASK_STATUS
        self.event_bus.publish(event)

    @property
    def playlist_items(self) -> list[str | None]:
        """
        returns names of every video in playlist.
        Empty is single video is downloaded.
        Missing names will be represented as None
        """

        return self._playlist_items

    @property
    def playlist_ord(self) -> int | None:
        info = self._service.progress_dict.get('info_dict') or {}
        pos = info.get('playlist_autonumber')
        return pos - 1 if pos is not None else None

    def get_metadata(self) -> None:
        try:
            info = self._service.fetch_data()
        except Exception as e:
            self._meta_exception = e
            LOGGER.debug(f'Task {self.id} failed to get metadata', exc_info=e)
            self._title = 'failed to load'
            return

        self._title = info.get('title') or 'not found'
        entries = info.get('entries') or []
        self._playlist_items = [(item or {}).get('title') for item in entries]
        self._metadata = info

    def setup(self) -> bool:
        if self._setupped:
            LOGGER.debug(f'Task is already setupped. Operation skipped')
            return True

        try:
            self._service.validate()
        except Exception as e:
            self._exception = e
            self._change_status(TaskState.FAIL)
            return False

        self._exception = None
        self._setupped = True
        if self.status == TaskState.NOT_READY:
            self._change_status(TaskState.READY)
        return True

    def start(self) -> None:
        if self.status != TaskState.READY:
            if self.status == TaskState.PAUSED:
                LOGGER.debug(f'Trying to start task that is paused. Execution skipped')
                return
            else:
                raise TaskError(f'Task that is not READY or PAUSED can not be started')

        try:
            if self._metadata is None:
                raise TaskError(f'get_metadata routine did not finished properly. Routine error: {self._meta_exception}')
            self._change_status(TaskState.IN_PROCESS)
            self._service.download(self._metadata)
            self._change_status(TaskState.FINISHED)
        except StoppedService:
            if self.status != TaskState.PAUSED:
                self._change_status(TaskState.PAUSED)
        except Exception as e:
            self._exception = e
            self._change_status(TaskState.FAIL)

    def stop(self) -> None:
        if self.status in (TaskState.FINISHED, TaskState.FAIL, TaskState.PAUSED, TaskState.CANCELLED):
            return
        self._service.stop_event = True
        self._change_status(TaskState.PAUSED)

    def prepare_resume(self) -> None:
        if self.status != TaskState.PAUSED:
            raise TaskError('resumed can be only stopped task')
        self._service.stop_event = False
        if self._setupped:
            self._change_status(TaskState.READY)
        else:
            self._change_status(TaskState.NOT_READY)

    def delete_folder(self) -> None:
        try:
            shutil.rmtree(self._service.output_folder)
        except FileNotFoundError:
            pass
        except OSError:
            gc.collect()
            shutil.rmtree(self._service.output_folder, ignore_errors=True)

    def cancel(self) -> None:
        self.delete_folder()
        self._change_status(TaskState.CANCELLED)

    @staticmethod
    def _video_progress_state(d: dict[str, Any]) -> tuple[ProgressState, DownloadState]:
        """snapshot of current progress state"""

        status = d.get('status')
        speed = d.get('speed')
        if status == 'finished':
            return ProgressState(10, 10, speed), DownloadState.FINISHED

        done = d.get('downloaded_bytes')
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        progress_obj = ProgressState(done, total, speed)

        match status:
            case 'downloading':
                return progress_obj, DownloadState.DOWNLOADING
            case 'error':
                return progress_obj, DownloadState.ERROR
            case _:
                return progress_obj, DownloadState.DOWNLOADING

    @overload
    def get_current_video_progress(self, estimate: Literal[True]=True) -> tuple[EstimProgressState, DownloadState]: ...
    @overload
    def get_current_video_progress(self, estimate: Literal[False]) -> tuple[ProgressState, DownloadState]: ...

    def get_current_video_progress(self, estimate: bool=True) -> tuple[ProgressState | EstimProgressState, DownloadState]:
        if estimate:
            progress, state = self._progress
            return progress.estim_progress(), state
        return self._progress

    @overload
    def get_progress(self, estimate: Literal[True]=True) -> EstimProgressState: ...
    @overload
    def get_progress(self, estimate: Literal[False]) -> ProgressState: ...

    def get_progress(self, estimate: bool=True) -> ProgressState | EstimProgressState:
        d = self._service.progress_dict
        speed = d.get('speed')
        video_progress: ProgressState | EstimProgressState
        video_progress, _ = self._progress
        if estimate:
            video_progress = video_progress.estim_progress()

        if not self._service.is_playlist:
            return video_progress

        info = d.get('info_dict') or {}
        entries = info.get('n_entries')
        pos = info.get('playlist_autonumber')

        if entries is None or pos is None:
            if isinstance(video_progress, ProgressState):
                return ProgressState(None, None, speed)
            else:
                return EstimProgressState(None, None, speed)

        fract = 0.0
        if video_progress.current is not None and video_progress.total:
            video_fract = video_progress.current / video_progress.total
            fract = min(video_fract, 1.0)

        if isinstance(video_progress, ProgressState):
            return ProgressState(pos - 1 + fract, entries, speed)
        else:
            return EstimProgressState(pos - 1 + fract, entries, speed)
