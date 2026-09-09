from typing import Callable, Dict, FrozenSet, List, Optional

_HANDLERS: Dict[str, List[Callable]] = {}
_FOLDER_SNAPSHOTS: Dict[int, FrozenSet[str]] = {}


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


def diff_folders(window) -> Optional[dict]:
    window_id = window.id()
    folders = frozenset(window.folders())
    previous = _FOLDER_SNAPSHOTS.get(window_id)
    _FOLDER_SNAPSHOTS[window_id] = folders

    if previous is None:
        return None

    added = sorted(folders - previous)
    removed = sorted(previous - folders)

    if not added and not removed:
        return None

    return {
        "window_id": window_id,
        "added": added,
        "removed": removed,
        "folders": sorted(folders),
    }