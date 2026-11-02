from collections import defaultdict
from collections.abc import Callable
from typing import Generic, ParamSpec, cast

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
    UPDATED_PROGRESS = Event[[]]('updated_progress')


class EventBus:
    def __init__(self) -> None:
        self._subscribers: defaultdict[Event, set[Callable[..., None]]] = defaultdict(set)
        self._once: defaultdict[Event, set[Callable[..., None]]] = defaultdict(set)

    def subscribe(self, event: Event[P], cb: Callable[P, None]) -> None:
        """subscribe callable on given event"""

        self._subscribers[event].add(cb)

    def subscribe_once(self, event: Event[P], cb: Callable[P, None]) -> None:
        """
        subscribe callable on given event, that automaticly removes after execution./n
        Handle for registered callable is returned./n/n
        Input callable and registered callable is not the same !
        """

        self._subscribers[event].add(cb)
        self._once[event].add(cb)

    def unsubscribe(self, event: Event[P], cb: Callable[P, None]) -> None:
        """unsubsctibe callable in given event. Does nothing, if event is not registered"""

        register = self._subscribers.get(event)
        if register:
            register.discard(cb)
        register_once = self._once.get(event)
        if register_once:
            register_once.discard(cb)

    def publish(self, event: Event[P], *args: P.args, **kwargs: P.kwargs) -> None:
        """run all callable objects registered to current event with given params"""

        register = self._subscribers.get(event)
        if register:
            once = self._once.get(event, set())
            for cb in tuple(register):
                if cb in once:
                    self.unsubscribe(event, cast(Callable[P, None], cb))
                cb(*args, **kwargs)
