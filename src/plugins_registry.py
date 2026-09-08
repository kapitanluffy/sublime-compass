from typing import List

# Public API for compass plugins.
# External plugins import register_plugin from here and call it at import time:
#   from Compass Navigator.src.plugins_registry import register_plugin

_PLUGINS: List = []


def register_plugin(plugin) -> None:
    """
    Register a compass plugin. External packages call this once at import time.
    """
    _PLUGINS.append(plugin)


def get_plugins() -> List:
    """
    Return the list of registered plugins, in registration order.
    """
    return list(_PLUGINS)
