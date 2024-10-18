from ..plugin import reload

reload("src", [
    "stack_manager",
    "stack",
    "file",
    "sheet_group",
    "view_stack",
    "events",
    "utils",
    "core"
])
reload("src.commands")
reload("src.plugins.files")

from .plugins.files import CompassPluginFileStack, CompassPluginFilesListener
from .stack_manager import *
from .stack import *
from .file import *
from .sheet_group import *
from .commands import *
from .view_stack import *
from .events import *
from .utils import *
from .core import *

__all__ = [
    "File",
    "SheetGroup",
    "StackManager",
    "ViewStack",

    # core
    "load",

    # stack functions
    "STACK",
    "hydrate_stack",
    "cache_stack",
    "push_sheets",
    "remove_sheet",
    "remove_window",

    # functions
    "build_stack",
    "list_files",
    "generate_view_meta",
    "guess_sheet_name",
    "replace_spaces_with_spaces",
    "get_visible_lines",
    "generate_preview",
    "parse_sheet",

    # src.commands
    "CompassCloseCommand",
    "CompassMoveCommand",
    "CompassShowCommand",
    "CompassDumpStackCommand",
    "CompassClearCacheCommand",
    "CompassIndexFilesCommand",

    # src.events
    "CompassFocusListener",

    # Files
    "CompassPluginFileStack",
    "CompassPluginFilesListener"
]
