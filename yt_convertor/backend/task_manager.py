from __future__ import annotations
import asyncio
import random

from functools import partial
from typing import TypeVar

from yt_convertor.type import DownloadInfo
from .task_base import Task, TaskState
from .event_bus import EventBus, Events

import logging
LOGGER = logging.getLogger(__name__)

TaskT = TypeVar('TaskT', bound=Task)

class TaskManager:

    _inst: TaskManager | None = None
    _initialized = False

    def __new__(cls) -> TaskManager:
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __init__(self) -> None:
        if not self._initialized:
            self.loop_task: asyncio.Task | None = None
            self._task_registry: dict[int, Task] = {}
            self.running_routines: dict[int, asyncio.Task] = {}
            self.queue: asyncio.Queue[Task] = asyncio.Queue()
            self.semaphore = asyncio.Semaphore(3)
            self.event_bus = EventBus()

            self._initialized = True
            self.running_meta_routines: dict[int, asyncio.Task] = dict()

    def get_task(self, task_id: int, task_type: type[TaskT]) -> TaskT | None:
        task = self._task_registry[task_id]
        if isinstance(task, task_type):
            return task
        return None

    def generate_task_id(self) -> int:
        while (rand_int := random.randint(1, 10_000_000)) in self._task_registry.keys():
            pass
        return rand_int

    def _run_metadata_coro(self, task: Task) -> None:
        coro = asyncio.create_task(asyncio.to_thread(task.get_metadata))
        self.running_meta_routines[task.id] = coro
        coro.add_done_callback(partial(self._on_meta_done, task))

    async def _wait_for_metadata(self, task: Task) -> None:
        meta = self.running_meta_routines.pop(task.id, None)
        if meta is not None:
            await meta

    async def register(self, task_type: type[TaskT], download_info: DownloadInfo) -> TaskT:
        task_id = self.generate_task_id()
        task = task_type(download_info, task_id)
        self._run_metadata_coro(task)
        self._task_registry[task_id] = task
        await self.queue.put(task)
        LOGGER.debug(f'task {task.id} added to queue:' + repr(task))
        return task

    def _on_meta_done(self, task: Task, fut: asyncio.Task) -> None:
        if fut.cancelled():
            return
        exc = fut.exception()
        if exc is not None:
            LOGGER.error(f'task {task.id}: getting metadata failed', exc_info=exc)
        self.event_bus.publish(Events.CHANGED_META)

    async def start_new_task(self, task: Task) -> None:
        is_setup = task.setup()
        if not is_setup:
            LOGGER.critical(f'task is unable to setup. Skipping task', exc_info=task.fail)
            return
        LOGGER.debug(f'task {task.id} is correctly setupped. Going to be executed')
        await self.start_task(task)

    async def start_task(self, task: Task) -> None:
        await self._wait_for_metadata(task)
        await asyncio.to_thread(task.start)
        LOGGER.debug(f'task {task.id} finished. Status: {task.status}')
        if task.status == TaskState.FAIL:
            LOGGER.debug(f'error messege: ', exc_info=task.fail)

    async def pause_task(self, task: Task):
        task.stop()
        routine = self.running_routines.get(task.id)
        if routine is not None:
            await asyncio.shield(routine)
        LOGGER.debug(f'task {task.id} is paused')

    async def stop_task(self, task: Task):
        await self.pause_task(task)
        task.cancel()
        LOGGER.debug(f'task {task.id} is stopped')

    async def resume_task(self, task: Task):
        task.prepare_resume()
        await self.queue.put(task)
        LOGGER.debug(f'task {task.id} is resumed')

    async def _run_one(self, task: Task):
        try:
            async with self.semaphore:
                if task.status == TaskState.NOT_READY:
                    await self.start_new_task(task)
                elif task.status == TaskState.READY:
                    await self.start_task(task)
                else:
                    LOGGER.critical(f'unexprected task state in queue: {task.status}')
        finally:
            self.running_routines.pop(task.id, None)

    async def _loop(self) -> None:
        while True:
            task = await self.queue.get()
            routine = asyncio.create_task(self._run_one(task))
            self.running_routines[task.id] = routine

    def start(self):
        if self.loop_task is not None:
            LOGGER.warning(
                'TaskManager is started while already running. Operation skipped'
            )
            return
        self.loop_task = asyncio.create_task(self._loop())

    async def shutdown(self):
        if self.loop_task is None:
            LOGGER.warning(
                'TaskManager is stopped while not ever running. Operation skipped'
            )
            return

        self.loop_task.cancel()
        self.loop_task = None

        while not self.queue.empty():
            self.queue.get_nowait()

        terminal_state = (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED)
        stops = [
            self.stop_task(task)
            for task_id in self.running_routines.copy().keys()
            if (task := self._task_registry[task_id]).status not in terminal_state
        ]
        await asyncio.gather(*stops, return_exceptions=True)
