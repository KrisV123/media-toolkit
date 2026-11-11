from textual import on
from textual.events import Mount
from textual.widgets import Static, Label, Button, ProgressBar
from textual.widget import Widget

from collections.abc import Iterable

from media_toolkit.backend.task_manager import TaskManager, Events

from media_toolkit.type import VIDEO_FORMATS
from media_toolkit.protocols import TaskSupportBasics
from media_toolkit.task_types import TaskState

from .messages import UpdateBorderTitle, RestartRequested, TaskStatusChanged

import logging
LOGGER = logging.getLogger(__name__)

ICONS = {
    TaskState.NOT_READY: '🟡',
    TaskState.READY: '▶',
    TaskState.IN_PROCESS: '⌛',
    TaskState.FINISHED: '✔ ',
    TaskState.FAIL: '❌',
    TaskState.PAUSED: '⏸️',
    TaskState.CANCELLED: '⏹️'
}

class QualityLabels(Static):
    def __init__(self, backend_task: TaskSupportBasics):
        super().__init__()
        download_info = backend_task.download_info
        self.format = download_info.format
        self.audio_quality = download_info.audio_quality
        self.video_quality = download_info.video_quality

    def compose(self) -> Iterable[Widget]:
        yield Label(content='audio quality: ' + self.audio_quality, id="audio-quality-label")
        if self.format in VIDEO_FORMATS:
            yield Label(content='video quality: ' + self.video_quality, id="video-quality-label")


class DownloadLabels(Static):
    def __init__(self, backend_task: TaskSupportBasics):
        super().__init__()
        download_info = backend_task.download_info
        self.format = download_info.format
        self.audio_quality = download_info.audio_quality
        self.video_quality = download_info.video_quality
        self.backend_task = backend_task

        self.fallback_label: Label | None = None

    def compose(self) -> Iterable[Widget]:
        yield Label(content='format: ' + self.format, id="format-label")
        yield QualityLabels(self.backend_task)

    def update_fallback(self) -> None:
        if self.fallback_label:
            return
        fallback = self.backend_task.check_fallback(None)
        if not fallback:
            return
        miss_flags = ', '.join(miss for miss in fallback)
        self.fallback_label = Label(content="  ↪ " + miss_flags, id='fallback-label')
        self.mount(self.fallback_label)


class ProgressButtons(Static):
    def __init__(self, backend_task: TaskSupportBasics):
        super().__init__()
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield Button(label='pause', compact=True, id='pause_resume_restart')
        yield Button(label='stop', compact=True, id='stop')

    async def run_pause_resume_restart(self, button: Button) -> None:
        manager = TaskManager()
        button.disabled = True
        if button.has_class('restart'):
            self.post_message(RestartRequested(self.backend_task.download_info))
        elif button.has_class('is_paused'):
            button.remove_class('is_paused')
            button.label = 'pause'
            await manager.resume_task(self.backend_task.id)
            self.post_message(TaskStatusChanged())
        else:
            button.add_class('is_paused')
            button.label = 'resume'
            await manager.pause_task(self.backend_task.id)
            self.post_message(TaskStatusChanged())
        button.disabled = False

    async def run_stop(self, button: Button) -> None:
        button.disabled = True
        button.label = 'stopped'

        restart_button = self.query_one('#pause_resume_restart', Button)
        restart_button.disabled = True
        if restart_button.has_class('is_paused'):
            restart_button.remove_class('is_paused')
        restart_button.add_class('restart')
        restart_button.label = 'restart'

        await TaskManager().stop_task(self.backend_task.id)
        self.post_message(TaskStatusChanged())
        restart_button.disabled = False

    @on(Button.Pressed, '#pause_resume_restart')
    async def on_pause_resume_restart(self, event: Button.Pressed) -> None:
        button = event.button
        await self.run_pause_resume_restart(button)

    @on(Button.Pressed, '#stop')
    async def on_stop(self, event: Button.Pressed) -> None:
        button = event.button
        await self.run_stop(button)


class Progress(Static):
    def __init__(self, backend_task: TaskSupportBasics):
        super().__init__()
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield ProgressBar(total=100, id="progress-bar")
        yield ProgressButtons(self.backend_task)

    def on_mount(self, event: Mount) -> None:
        self.progress_bar = self.query_one('#progress-bar', ProgressBar)
        self._timer = self.set_interval(0.1, self.update_progress_bar)
        self._is_timer_paused = False

    def update_progress_bar(self) -> None:
        state = self.backend_task.get_progress()

        if state.current is None:
            self.progress_bar.update(total=state.total)
        else:
            self.progress_bar.update(total=state.total, progress=state.current)

        status = self.backend_task.status
        if status in (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED):
            self._timer.stop()
            self._is_timer_paused = True
            self.post_message(TaskStatusChanged())
            if self.progress_bar.total is None:
                self.progress_bar.update(total=1)

    def on_task_status_changed(self, messege: TaskStatusChanged) -> None:
        status = self.backend_task.status
        if status == TaskState.PAUSED and not self._is_timer_paused:
            self._timer.pause()
            self._is_timer_paused = True
        elif status in (TaskState.IN_PROCESS, TaskState.READY) and self._is_timer_paused:
            self._timer.resume()
            self._is_timer_paused = False


class DownloadItem[T:TaskSupportBasics=TaskSupportBasics](Static):
    can_focus = True

    BINDINGS = [
        ('p', 'pause_resume_restart', 'puase/resume/restart'),
        ('s', 'stop', 'Stop')
    ]

    def __init__(self, backend_task: T):
        super().__init__()
        download_info = backend_task.download_info
        self.format = download_info.format
        self.audio_quality = download_info.audio_quality
        self.video_quality = download_info.video_quality
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        """
        this method must me only extended. At the beggining use\n
        yield from super().compose()
        """

        yield DownloadLabels(self.backend_task)
        yield Progress(self.backend_task)

    def post_update_border_title(self) -> None:
        self.post_message(UpdateBorderTitle())

    def on_mount(self) -> None:
        meta_event = Events.CHANGED_META
        self.backend_task.event_bus.subscribe(meta_event, self.post_update_border_title)
        status_event = Events.UPDATE_TASK_STATUS
        self.backend_task.event_bus.subscribe(status_event, self.post_update_border_title)

        self.border_title = f'{ICONS[self.backend_task.status]}  {self.backend_task.title}'
        self.border_subtitle = str(self.backend_task.id)

    def on_update_border_title(self) -> None:
        current_state_emoji = ICONS[self.backend_task.status]
        self.border_title = f'{current_state_emoji}  {self.backend_task.title}'

    async def action_pause_resume_restart(self) -> None:
        button = self.query_one('#pause_resume_restart', Button)
        await self.query_one(ProgressButtons).run_pause_resume_restart(button)

    async def action_stop(self) -> None:
        button = self.query_one('#stop', Button)
        await self.query_one(ProgressButtons).run_stop(button)
