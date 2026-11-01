import shutil
import gc
from typing import Any

from media_toolkit.type import DownloadInfo
from media_toolkit.protocols import TaskSupportsCollection
from media_toolkit.task_types import TaskState, DownloadState

from media_toolkit.backend import Task, TaskError
from media_toolkit.backend.event_bus import Events
from media_toolkit.backend.task_base import Task, TaskState, ProgressState, TaskError
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
        self._title: str = "..."
        self._playlist_items: list[str | None] = []
        self._metadata: dict[str, Any] | None = None
        self._meta_exception: Exception | None = None

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
        try:
            self._service.validate()
        except Exception as e:
            self._exception = e
            self._change_status(TaskState.FAIL)
            return False

        self._exception = None
        self._change_status(TaskState.READY)
        return True

    def start(self) -> None:
        try:
            if self._metadata is None:
                raise TaskError(f'get_metadata routine did not finished properly. Routine error: {self._meta_exception}')
            self._change_status(TaskState.IN_PROCESS)
            self._service.download(self._metadata)
            self._change_status(TaskState.FINISHED)
        except StoppedService:
            self._change_status(TaskState.PAUSED)
        except Exception as e:
            self._change_status(TaskState.FAIL)
            self._exception = e

    def stop(self) -> None:
        if self.status in (TaskState.FINISHED, TaskState.FAIL, TaskState.PAUSED):
            return
        self._service.stop_event = True

    def prepare_resume(self) -> None:
        if self.status != TaskState.PAUSED:
            raise TaskError('resumed can be only stopped task')
        self._service.stop_event = False
        self._change_status(TaskState.READY)

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
        if status == 'finished':
            return ProgressState(10, 10), DownloadState.FINISHED

        done = d.get('downloaded_bytes')
        total = d.get('total_bytes') or d.get('total_bytes_estimate')
        progress_obj = ProgressState(done, total)

        match status:
            case 'downloading':
                return progress_obj, DownloadState.DOWNLOADING
            case 'error':
                return progress_obj, DownloadState.ERROR
            case _:
                return progress_obj, DownloadState.DOWNLOADING

    def current_video_progress(self) -> tuple[ProgressState, DownloadState]:
        """
        returns progress of current downloaded video.
        If single video is downloaded, works same as progress.
        """

        return self._video_progress_state(self._service.progress_dict)

    def progress(self) -> ProgressState:
        d = self._service.progress_dict
        video_progress, _ = self._video_progress_state(d)

        if not self._service.is_playlist:
            return video_progress

        info = d.get('info_dict') or {}
        entries = info.get('n_entries')
        pos = info.get('playlist_autonumber')
        if entries is None or pos is None:
            return ProgressState(None, None)

        fract = 0.0
        if video_progress.current is not None and video_progress.total:
            video_fract = video_progress.current / video_progress.total
            fract = min(video_fract, 1.0)
        return ProgressState(pos - 1 + fract, entries)
