from collections import defaultdict
from collections.abc import Callable
from typing import Generic, ParamSpec

P = ParamSpec('P')

class Event(Generic[P]):
    def __init__(self, name: str):
        self.name = name
        self.signature = P

    def __repr__(self) -> str:
        return f'Event: {self.name}'

    def __str__(self) -> str:
        return f'Event: {self.name}'


class Events:
    CHANGED_META = Event[[]]('changed_meta')
    UPDATE_TASK_STATUS = Event[[]]('update_task_status')


class EventBus:
    def __init__(self) -> None:
        self.subscribers: defaultdict[Event, set[Callable[..., None]]] = defaultdict(set)

    def subscribe(self, event: Event[P], cb: Callable[P, None]) -> None:
        self.subscribers[event].add(cb)

    def unsubsrcribe(self, event: Event[P], cb: Callable[P, None]) -> None:
        self.subscribers[event].discard(cb)

    def publish(self, event: Event[P], *args: P.args, **kwargs: P.kwargs) -> None:
        for cb in tuple(self.subscribers[event]):
            cb(*args, **kwargs)
