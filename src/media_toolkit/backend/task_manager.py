import asyncio
import random

from functools import partial

from media_toolkit.type import DownloadInfo
from .task_base import Task, TaskState
from .event_bus import EventBus, Events

import logging
LOGGER = logging.getLogger(__name__)

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

    def _get_task(self, task_id: int) -> Task:
        return self._task_registry[task_id]

    def generate_task_id(self) -> int:
        while (rand_int := random.randint(1, 10_000_000)) in self._task_registry.keys():
            pass
        return rand_int

    def _run_metadata_coro(self, task_id: int) -> None:
        task = self._get_task(task_id)
        coro = asyncio.create_task(asyncio.to_thread(task.get_metadata))
        self.running_meta_routines[task.id] = coro
        coro.add_done_callback(partial(self._on_meta_done, task))

    async def _wait_for_metadata(self, task_id: int) -> None:
        meta = self.running_meta_routines.pop(task_id, None)
        if meta is not None:
            await meta

    async def register[T: Task](self, task_type: type[T], download_info: DownloadInfo) -> T:
        task_id = self.generate_task_id()
        task = task_type(download_info, task_id)
        self._task_registry[task_id] = task
        self._run_metadata_coro(task_id)
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

    async def start_new_task(self, task_id: int) -> None:
        task = self._get_task(task_id)
        is_setup = task.setup()
        if not is_setup:
            LOGGER.critical(f'task is unable to setup. Skipping task', exc_info=task.fail)
            return
        LOGGER.debug(f'task {task_id} is correctly setupped. Going to be executed')
        await self.start_task(task_id)

    async def start_task(self, task_id: int) -> None:
        task = self._get_task(task_id)
        await self._wait_for_metadata(task_id)
        await asyncio.to_thread(task.start)
        LOGGER.debug(f'task {task_id} finished. Status: {task.status}')
        if task.status == TaskState.FAIL:
            LOGGER.debug(f'error messege: ', exc_info=task.fail)

    async def pause_task(self, task_id: int) -> None:
        task = self._get_task(task_id)
        task.stop()
        routine = self.running_routines.get(task_id)
        if routine is not None:
            await asyncio.shield(routine)
        LOGGER.debug(f'task {task_id} is paused')

    async def stop_task(self, task_id: int) -> None:
        task = self._get_task(task_id)
        await self.pause_task(task_id)
        task.cancel()
        LOGGER.debug(f'task {task_id} is stopped')

    async def resume_task(self, task_id: int) -> None:
        task = self._get_task(task_id)
        task.prepare_resume()
        await self.queue.put(task)
        LOGGER.debug(f'task {task_id} is resumed')

    async def _run_one(self, task_id: int) -> None:
        task = self._get_task(task_id)
        try:
            async with self.semaphore:
                if task.status == TaskState.NOT_READY:
                    await self.start_new_task(task_id)
                elif task.status == TaskState.READY:
                    await self.start_task(task_id)
                else:
                    LOGGER.critical(f'unexprected task state in queue: {task.status}')
        finally:
            self.running_routines.pop(task.id, None)

    async def _loop(self) -> None:
        while True:
            task = await self.queue.get()
            routine = asyncio.create_task(self._run_one(task.id))
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
            self.stop_task(task_id)
            for task_id in self.running_routines.copy().keys()
            if self._task_registry[task_id].status not in terminal_state
        ]
        await asyncio.gather(*stops, return_exceptions=True)
