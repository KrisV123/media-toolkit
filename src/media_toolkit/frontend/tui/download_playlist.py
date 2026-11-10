from textual.events import Mount
from textual.strip import Strip
from textual.widgets import Label
from textual.widget import Widget

from textual.strip import Strip
from textual.geometry import Size, Region
from rich.segment import Segment

from collections.abc import Iterable
from dataclasses import dataclass

from media_toolkit.backend import Events
from media_toolkit.protocols import TaskSupportsCollection
from media_toolkit.task_types import EstimProgressState, TaskState, DownloadState

from .download_helpers import DownloadItem
from .messages import StartTick, TaskStatusChanged

SOLO_ICONS = {
    DownloadState.DOWNLOADING: '⌛',
    DownloadState.FINISHED: '✔ ',
    DownloadState.ERROR: '❌'
}

@dataclass(slots=True)
class DownloadLine:
    icon: DownloadState
    percentage: int
    title: str | None
    fallback: str | None


class PlaylistCatalog(Widget):
    def __init__(self, backend_task: TaskSupportsCollection):
        super().__init__()
        self.backend_task = backend_task
        self.download_data: list[DownloadLine] = []

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        return len(self.download_data)

    def render_line(self, y: int) -> Strip:
        base_style = self.rich_style

        if y >= len(self.download_data):
            return Strip.blank(self.size.width, base_style)

        download_line = self.download_data[y]
        left_part = Strip((
            Segment(SOLO_ICONS[download_line.icon]),
            Segment(" " * 2),
            Segment(f'{download_line.percentage:3d}'),
            Segment(" %" + " " * 2),
            Segment(download_line.title or "failed to load"),
        ))
        fallback_text = download_line.fallback if download_line.fallback else ""
        fallback_len = len(fallback_text)

        width = self.size.width
        left_part = left_part.adjust_cell_length(max(0, width - fallback_len))
        right_part = Strip((Segment(fallback_text),))
        return Strip.join((left_part, right_part)).apply_style(base_style)

    def post_start_tick(self) -> None:
        self.post_message(StartTick())

    def _on_mount(self, event: Mount) -> None:
        if len(self.backend_task.playlist_items) == 0:
            meta_event = Events.CHANGED_META
            self.backend_task.event_bus.subscribe_once(meta_event, self.post_start_tick)
        else:
            self.on_start_tick()

    def on_start_tick(self):
        self.load_data()
        self._timer = self.set_interval(0.1, self.update_data)
        self._is_timer_paused = False

    def load_data(self) -> None:
        self.download_data = [
            DownloadLine(DownloadState.DOWNLOADING, 0, title, None)
            for title in self.backend_task.playlist_items
        ]
        self.refresh(layout=True)

    def update_data(self) -> None:
        self.update_download_end()

        ord = self.backend_task.playlist_ord
        if ord is None:
            return

        is_dirty_set: set[bool] = set()
        progress, video_status = self.backend_task.get_current_video_progress()
        is_dirty_set.add(self.update_percentage(ord, progress))
        is_dirty_set.add(self.update_video_end(ord, video_status))

        if any(is_dirty_set):
            self.refresh(Region(0, ord, self.size.width, 1))

    def update_download_end(self) -> None:
        task_status = self.backend_task.status
        if task_status in (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED):
            self._timer.stop()

    def update_video_end(self, ord: int, video_status: DownloadState) -> bool:
        if video_status in (DownloadState.FINISHED, DownloadState.ERROR):
            self.download_data[ord].icon = video_status
            self.update_fallback(ord)
            return True
        return False

    def update_percentage(self, ord: int, progress: EstimProgressState) -> bool:
        if progress.total is not None and progress.current:
            progress_num = int((progress.current / progress.total) * 100)
            curr_progress_num = self.download_data[ord].percentage
            if curr_progress_num != progress_num:
                self.download_data[ord].percentage = progress_num
                return True
            return False
        return False

    def update_fallback(self, ord: int) -> bool:
        fallback = self.backend_task.check_fallback(ord)
        if not fallback:
            return False
        padding = ' ' * 3
        miss_flags = padding + '↪ ' + ', '.join(miss for miss in fallback)
        self.download_data[ord].fallback = miss_flags
        return True

    def sync_timer(self) -> None:
        if self._timer is None:
            return

        status = self.backend_task.status
        if status == TaskState.PAUSED and not self._is_timer_paused:
            self._timer.pause()
            self._is_timer_paused = True
        elif status in (TaskState.IN_PROCESS, TaskState.READY) and self._is_timer_paused:
            self._timer.resume()
            self._is_timer_paused = False


class DownloadPlaylistWidget(DownloadItem[TaskSupportsCollection]):
    def compose(self) -> Iterable[Widget]:
        yield from super().compose()
        yield PlaylistCatalog(self.backend_task)

    def on_task_status_changed(self, messege: TaskStatusChanged) -> None:
        self.query_one(PlaylistCatalog).sync_timer()
        status = self.backend_task.status
        if status == TaskState.FAIL:
            self.mount(Label(f'{str(self.backend_task.fail)}'))
