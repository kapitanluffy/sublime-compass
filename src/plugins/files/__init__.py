from .file import *
from .stack import *
from .events import *

from ...plugins_registry import register_plugin

register_plugin(CompassPluginFileStack())

__all__ = [
    "CompassPluginFileStack",
    "CompassPluginFilesListener",
]
