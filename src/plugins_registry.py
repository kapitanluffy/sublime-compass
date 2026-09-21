from typing import List

from ..utils import plugin_debug

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
