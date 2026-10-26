from textual.events import Mount
from textual.widgets import Static, Label, Button, ProgressBar
from textual.widget import Widget

from collections.abc import Iterable

from yt_convertor.type import VIDEO_FORMATS
from .messages import Changed, Restart
from yt_convertor.backend.task_base import Task, TaskState
from yt_convertor.backend.task_manager import TaskManager

ICONS = {
    TaskState.NOT_READY: '🟡',
    TaskState.READY: '▶',
    TaskState.IN_PROCESS: '⌛',
    TaskState.FINISHED: '✔ ',
    TaskState.FAIL: '❌',
    TaskState.PAUSED: '⏸️',
    TaskState.CANCELLED: '⏹️'
}

class DownloadLabels(Static):
    def __init__(self, format: str, audio_quality: str, video_quality: str):
        super().__init__()
        self.format = format
        self.audio_quality = audio_quality
        self.video_quality = video_quality

    def compose(self) -> Iterable[Widget]:
        yield Label(content='format: ' + self.format, id="format-label")
        yield Label(content='audio quality: ' + self.audio_quality, id="audio-quality-label")
        if self.format in VIDEO_FORMATS:
            yield Label(content='video quality: ' + self.video_quality, id="video-quality-label")


class ProgressButtons(Static):
    def __init__(self, backend_task: Task):
        super().__init__()
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield Button(label='pause', compact=True, id='pause_resume_restart')
        yield Button(label='stop', compact=True, id='stop')

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        manager = TaskManager()

        if button.id == 'pause_resume_restart':
            button.disabled = True
            if button.has_class('restart'):
                self.post_message(Restart(self.backend_task.download_info))
            elif button.has_class('is_paused'):
                button.remove_class('is_paused')
                button.label = 'pause'
                await manager.resume_task(self.backend_task)
                self.post_message(Changed(TaskState.IN_PROCESS))
            else:
                button.add_class('is_paused')
                button.label = 'resume'
                await manager.pause_task(self.backend_task)
                self.post_message(Changed(TaskState.PAUSED))
            button.disabled = False

        elif button.id == 'stop':
            button.disabled = True            
            button.label = 'stopped'

            restart_button = self.query_one('#pause_resume_restart', Button)
            restart_button.disabled = True
            if restart_button.has_class('is_paused'):
                restart_button.remove_class('is_paused')
            restart_button.add_class('restart')
            restart_button.label = 'restart'

            await manager.stop_task(self.backend_task)
            self.post_message(Changed(TaskState.CANCELLED))
            restart_button.disabled = False


class Progress(Static):

    def __init__(self, backend_task: Task):
        super().__init__()
        self.backend_task = backend_task

    def compose(self) -> Iterable[Widget]:
        yield ProgressBar(total=100, id="progress-bar")
        yield ProgressButtons(self.backend_task)

    def on_mount(self, event: Mount) -> None:
        self.progress_bar = self.query_one('#progress-bar', ProgressBar)
        self._timer = self.set_interval(0.3, self.update_progress_bar)

    def update_progress_bar(self) -> None:
        state = self.backend_task.progress()
        if state.current is None:
            self.progress_bar.update(total=state.total)
        else:
            self.progress_bar.update(total=state.total, progress=state.current)

        status = self.backend_task.status
        if status in (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED):
            self._timer.stop()
            self.post_message(Changed(status))
