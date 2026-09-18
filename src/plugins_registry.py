from typing import List

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


def register_plugin(plugin) -> None:
    """
    Register a compass plugin. External packages call this once inside
    plugin_loaded() (see module comment). In-tree callers use import time
    only for bundled plugins.
    """
    _PLUGINS.append(plugin)


def get_plugins() -> List:
    """
    Return the list of registered plugins, in registration order.
    """
    return list(_PLUGINS)
