from typing import Callable, Dict, List

_HANDLERS: Dict[str, List[Callable]] = {}


def subscribe(event: str, handler: Callable):
    handlers = _HANDLERS.get(event)

    if handlers is None:
        _HANDLERS[event] = [handler]
        return

    if handler not in handlers:
        handlers.append(handler)


def emit(event: str, **payload):
    handlers = _HANDLERS.get(event)

    if not handlers:
        return

    for handler in list(handlers):
        handler(**payload)