from .plugin import _PLUGIN_INSTANCE, CompassPluginFileStack

from ...plugins_registry import register_plugin

register_plugin(_PLUGIN_INSTANCE)

__all__ = [
    "CompassPluginFileStack",
]
