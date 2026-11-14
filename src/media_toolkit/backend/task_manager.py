import asyncio
import random
import itertools

from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import assert_never

from media_toolkit.type import DownloadInfo
from .task_base import Task, TaskState
from .event_bus import Events

import logging
LOGGER = logging.getLogger(__name__)

type Order = int

class Priority(IntEnum):
    OVERTAKE = auto()
    RESUMED = auto()
    BASIC = auto()


class StablePriorityQueue[T]:
    def __init__(self) -> None:
        self.queue: asyncio.PriorityQueue[tuple[Priority, Order, T]] = asyncio.PriorityQueue()
        self.order = itertools.count()

    def _iter_order(self) -> int:
        return next(self.order)

    async def put(self, item: T, priority: Priority) -> None:
        await self.queue.put((priority, self._iter_order(), item))

    async def get(self) -> T:
        _, _, item = await self.queue.get()
        return item

    def get_nowait(self) -> T:
        _, _, item = self.queue.get_nowait()
        return item

    def qsize(self) -> int:
        return self.queue.qsize()

    def empty(self) -> bool:
        return self.queue.empty()


type Task_id = int

@dataclass(slots=True)
class RegistryItem:
    task: Task
    pending: bool
    not_running: asyncio.Event = field(default_factory=asyncio.Event)

    def __post_init__(self) -> None:
        self.not_running.set()


class TaskManager:
    _inst: TaskManager | None = None
    _initialized = False

    def __new__(cls) -> TaskManager:
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __init__(self) -> None:
        if not self._initialized:
            self.workers: list[asyncio.Task] = []
            self.workers_ammount = 3

            self.metadata_workers: list[asyncio.Task] = []
            self.metadata_workers_ammount = 3

            self.task_queue: StablePriorityQueue[Task_id] = StablePriorityQueue()
            self.metadata_queue: asyncio.Queue[Task_id] = asyncio.Queue()
            self._task_registry: dict[Task_id, RegistryItem] = {}
            self._initialized = True

    def generate_id(self) -> int:
        while (rand_int := random.randint(1, 10_000_000)) in self._task_registry.keys():
            pass
        return rand_int

    def _get_registry_item(self, task_id: Task_id) -> RegistryItem:
        return self._task_registry[task_id]

    async def register[T: Task](self, task_type: type[T], download_info: DownloadInfo) -> T:
        task = task_type(download_info, self.generate_id())
        registry_item = RegistryItem(task, True)
        self._task_registry[task.id] = registry_item
        await self.metadata_queue.put(task.id)
        LOGGER.debug(f'task {task.id} added to metadata queue:' + repr(task))
        return task

    async def _start_new_task(self, task: Task) -> None:
        is_setup = task.setup()
        if not is_setup:
            LOGGER.critical(
                f'task {task.id} is unable to setup. Skipping task', exc_info=task.fail
            )
            return
        LOGGER.debug(f'task {task.id} is correctly setupped. Going to be executed')
        await self._start_task(task)

    async def _start_task(self, task: Task) -> None:
        registry_item = self._get_registry_item(task.id)
        try:
            registry_item.not_running.clear()
            await asyncio.to_thread(task.start)
            LOGGER.debug(f'task {task.id} finished. Status: {task.status}')
            if task.status == TaskState.FAIL:
                LOGGER.debug(f'task {task.id} error messege: ', exc_info=task.fail)
        finally:
            registry_item.not_running.set()

    async def pause_task(self, task_id: Task_id) -> None:
        registry_item = self._get_registry_item(task_id)
        registry_item.task.stop()
        await registry_item.not_running.wait()
        LOGGER.debug(f'task {task_id} is paused')

    async def stop_task(self, task_id: int) -> None:
        registry_item = self._get_registry_item(task_id)
        await self.pause_task(task_id)
        registry_item.task.cancel()
        LOGGER.debug(f'task {task_id} is stopped')

    async def resume_task(self, task_id: int) -> None:
        registry_item = self._get_registry_item(task_id)
        await registry_item.not_running.wait()
        registry_item.task.prepare_resume()
        if not registry_item.pending:
            registry_item.pending = True
            await self.task_queue.put(task_id, Priority.RESUMED)
        LOGGER.debug(f'task {task_id} is resumed')

    async def _run_task(self, task_id: Task_id) -> None:
        registry_item = self._get_registry_item(task_id)
        task = registry_item.task
        match task.status:
            case TaskState.NOT_READY:
                await self._start_new_task(task)
            case TaskState.READY:
                await self._start_task(task)
            case TaskState.PAUSED:
                registry_item.pending = False
                return
            case TaskState.IN_PROCESS:
                LOGGER.critical(
                    f'already running task is in another worker. Task is skipped. task_id: {task_id}'
                )
            case TaskState.FINISHED | TaskState.CANCELLED | TaskState.FAIL:
                return
            case _:
                assert_never(task.status)

    async def _run_metadata(self, task_id: Task_id) -> None:
        registry_item = self._get_registry_item(task_id)
        task = registry_item.task
        try:
            await asyncio.to_thread(task.get_metadata)
        except Exception as e:
            LOGGER.debug(f'task {task.id} failed to get metadata', exc_info=e)
        finally:
            task.event_bus.publish(Events.CHANGED_META)

    async def _worker(self) -> None:
        while True:
            id = await self.task_queue.get()
            registry_item = self._get_registry_item(id)
            registry_item.pending = False
            try:
                await self._run_task(id)
            except Exception as e:
                LOGGER.critical('worker with task {id} failed', exc_info=e)

    async def _metadata_worker(self) -> None:
        while True:
            id = await self.metadata_queue.get()
            await self._run_metadata(id)
            registry_item = self._get_registry_item(id)
            task = registry_item.task
            await self.task_queue.put(task.id, Priority.BASIC)
            LOGGER.debug(f'task {task.id} added to queue:' + repr(task))

    def start(self):
        self.workers = [
            asyncio.create_task(self._worker())
            for _ in range(self.workers_ammount)
        ]
        self.metadata_workers = [
            asyncio.create_task(self._metadata_worker())
            for _ in range(self.metadata_workers_ammount)
        ]

    async def shutdown(self) -> None:
        for worker in self.metadata_workers:
            worker.cancel()
        for worker in self.workers:
            worker.cancel()

        while not self.metadata_queue.empty():
            self.metadata_queue.get_nowait()

        while not self.task_queue.empty():
            id = self.task_queue.get_nowait()
            self._get_registry_item(id).pending = False

        terminal_state = (TaskState.FINISHED, TaskState.FAIL, TaskState.CANCELLED)

        for id in tuple(self._task_registry):
            registry_item = self._task_registry[id]
            if registry_item.task.status not in terminal_state:
                await self.stop_task(id)

        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
