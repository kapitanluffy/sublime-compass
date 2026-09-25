"""Central cache service - Compass Navigator core.

Core owns where + when persistence happens: the window.settings()
medium, the throttle timing, and the lifecycle triggers (callers in
events.py, view_stack.py, show.py, core.py). Plugins own what their
data means and never touch this module's callers — today that means
the MRU STACK (settings key + tuple format frozen); the same
primitives serve future plugin caches (Files index, recency).
"""

from time import time
from typing import Dict
import sublime

from ..utils import plugin_settings

__all__ = [
    "cache_throttle",
    "read_cache",
    "write_cache",
]

_CACHE_UPDATE_TIMES: Dict[str, float] = {}


def cache_throttle() -> int:
    throttle = int(plugin_settings().get("stack_cache_throttle", 30))
    return max(throttle, 30)


def read_cache(window: sublime.Window, key: str, default=[]):
    try:
        return window.settings().get(key, default)
    except Exception:
        return default


def write_cache(window: sublime.Window, key: str, data, force: bool = False) -> bool:
    # Throttle is per settings key. With a single key in use today
    # (compass_stack_cache) this behaves exactly like the old global
    # STACK_UPDATE_TIME; extra keys get independent budgets.
    now = time()
    if now - _CACHE_UPDATE_TIMES.get(key, 0) < cache_throttle() and force is not True:
        return False
    _CACHE_UPDATE_TIMES[key] = now
    window.settings().set(key, data)
    return True
