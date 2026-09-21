from typing import Dict, List

from ..utils import plugin_debug, plugin_settings

# Public API for compass plugins.
# External plugins must register inside plugin_loaded() only (never at import
# time), using importlib so a missing Compass disables silently:
#   import importlib
#   def plugin_loaded():
#       try:
#           registry = importlib.import_module("Compass Navigator.src.plugins_registry")
#           bus = importlib.import_module("Compass Navigator.src.event_bus")
#       except ImportError:
#           return
#       registry.register_plugin(MyPlugin())
#       bus.subscribe("compass_file_focused", on_focused)
# Use `Compass: Create Plugin` to scaffold this pattern.

_PLUGINS: List = []
_LOADED = False

# Selection history per plugin id: most-recent-first lists of opaque
# keys. In-memory only; plugins namespace their own keys (e.g. include
# the project id) so entries can never leak across scopes.
_RECENT: Dict[str, List] = {}


def _plugin_id(plugin) -> str:
    get_id = getattr(plugin, "get_id", None)
    if callable(get_id):
        try:
            return str(get_id())
        except Exception:
            pass
    return ""


def register_plugin(plugin) -> None:
    """
    Register a compass plugin. External packages call this once inside
    plugin_loaded() (see module comment). In-tree callers use import time
    only for bundled plugins.

    Re-registering an id replaces the entry, never duplicates it, so a
    Sublime reload cannot double-run a plugin's rows.
    """
    new_id = _plugin_id(plugin)
    if new_id:
        for index, existing in enumerate(_PLUGINS):
            if _plugin_id(existing) == new_id:
                _PLUGINS[index] = plugin
                return
    _PLUGINS.append(plugin)


def get_plugins() -> List:
    """
    Return the list of registered plugins, in registration order.
    Bundled plugins register at import time (before any external
    plugin_loaded runs), so they always come first.
    """
    return list(_PLUGINS)


def _recent_cap() -> int:
    try:
        raw = plugin_settings().get("max_recent_picks", 10)
    except Exception:
        return 10
    if raw is False:
        return 0
    try:
        cap = int(raw)  # type: ignore
    except Exception:
        return 10
    return cap if cap > 0 else 0


def _recency_enabled() -> bool:
    return _recent_cap() > 0


def record_selection(plugin_id: str, key) -> None:
    """
    Remember that the user picked key from plugin_id's rows. Call from
    on_select (never on_highlight — highlight fires on every arrow-key
    pass and would trash the ordering). Capped at max_recent_picks;
    a no-op when recency is disabled (max_recent_picks: false).
    """
    if not _recency_enabled():
        return
    try:
        recent = _RECENT.setdefault(plugin_id, [])
        if key in recent:
            recent.remove(key)
        recent.insert(0, key)
        del recent[_recent_cap():]
    except Exception:
        pass


def order_by_recent(plugin_id: str, keys: List):
    """
    Stable partition: recorded keys first (recency order, skipping ones
    no longer present), everything else in original order. O(cap * n),
    no sorting — safe for large indexes.
    """
    if not _recency_enabled():
        return list(keys)
    recent = _RECENT.get(plugin_id)
    if not recent:
        return list(keys)
    remaining = list(keys)
    ordered = []
    for key in recent:
        try:
            remaining.remove(key)
        except ValueError:
            continue
        ordered.append(key)
    ordered.extend(remaining)
    return ordered


def recent_keys(plugin_id: str) -> List:
    """
    Return a copy of plugin_id's recorded keys, most-recent-first.
    Use it to mark recent rows (e.g. annotations) in generate_items.
    """
    return list(_RECENT.get(plugin_id, []))


def load_plugins() -> None:
    """
    Central load entry point. Called once from core.load(): iterates the
    registry in registration order, skips disabled plugins, and calls
    on_load per plugin. One broken plugin cannot block the rest, and a
    second call within the same session is a no-op.
    """
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    for plugin in get_plugins():
        name = _plugin_id(plugin) or repr(plugin)
        try:
            is_enabled = plugin.is_enabled() if hasattr(plugin, "is_enabled") else True
        except Exception as e:
            print("Compass: skipping plugin %s (is_enabled raised %r)" % (name, e))
            continue
        if is_enabled is False:
            continue
        on_load = getattr(plugin, "on_load", None)
        if not callable(on_load):
            continue
        try:
            on_load()
        except Exception as e:
            print("Compass: plugin %s on_load failed: %r" % (name, e))
            plugin_debug("Compass: plugin %s on_load failed: %r" % (name, e))
