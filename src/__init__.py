from .plugins.files import CompassPluginFileStack, CompassPluginFilesListener
from .plugins.mru import CompassPluginMruTabs
from .stack import *
from .sheet_group import *
from .commands import *
from .view_stack import *
from .events import *
from .utils import *
from .core import *

__all__ = [
    "SheetGroup",
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
    "dict_deep_get",

    # src.commands
    "CompassCreatePluginCommand",
    "CompassCloseCommand",
    "CompassMoveCommand",
    "CompassShowCommand",
    "CompassDumpStackCommand",
    "CompassClearCacheCommand",
    "CompassIndexFilesCommand",
    "CompassBroadcastEventCommand",

    # src.events
    "CompassFocusListener",

    # Files
    "CompassPluginFileStack",
    "CompassPluginFilesListener",

    # MRU tabs
    "CompassPluginMruTabs",
]
