from ...plugin import reload

reload("src.commands", ["close", "move", "build_stack", "show", "dump_stack", "index_files"])

from .close import CompassCloseCommand
from .move import CompassMoveCommand
from .build_stack import CompassBuildStackCommand
from .show import CompassShowCommand
from .dump_stack import CompassDumpStackCommand
from .clear_cache import CompassClearCacheCommand
from .index_files import CompassIndexFilesCommand

__all__ = [
    "CompassCloseCommand",
    "CompassMoveCommand",
    "CompassBuildStackCommand",
    "CompassShowCommand",
    "CompassDumpStackCommand",
    "CompassClearCacheCommand",
    "CompassIndexFilesCommand",
]
