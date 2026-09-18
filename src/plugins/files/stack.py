from collections import OrderedDict
import os
import subprocess
from typing import List, Optional, Tuple, OrderedDict as TOrderedDict
import sublime

from ...utils import dict_deep_get, plugin_settings
from ..plugin_base import CompassPlugin
from .file import File

ITEM_TYPE = "compass_plugin_file_open_file"
CompassItemTuple = Tuple[int, int, List[int], int]
FILE_STACK: TOrderedDict[Tuple[str, str, str], Optional[CompassItemTuple]] = OrderedDict()
KIND_FILE_PLUGIN_FILE_ITEM_TYPE = (sublime.KindId.COLOR_YELLOWISH, "f", ITEM_TYPE)


class CompassItem():
    """
    A compass item points to a location in Sublime
    """

    def __init__(
        self,
        window: sublime.Window,
        sheets: List[sublime.Sheet],
        group: int = 0,
        focused: Optional[sublime.Sheet] = None,
    ):
        self.window = window
        self.sheets = sheets
        self.group = group
        self.focused = focused if focused is not None else self.sheets[0]

    def to_tuple(self):
        sheet_ids = [sheet.id() for sheet in self.sheets]
        return (self.window.id(), self.group, sheet_ids, self.focused.id())


class FilePluginItem():
    def __init__(self, file: File, item: Optional[CompassItem]):
        self.file = file
        self.item = item

    def key(self):
        file = self.file.get_full_path()
        folder = self.file.get_folder()
        window = self.file.get_window()
        return (file, folder, window)

    def value(self):
        item = self.item.to_tuple() if self.item is not None else None
        return item


class CompassPluginFileStack(CompassPlugin):
    @classmethod
    def get(cls, key: Tuple[str, str, str]):
        """
        Get an item from stack
        """
        if key in FILE_STACK:
            return FILE_STACK[key]
        return None

    @classmethod
    def remove(cls, key: Tuple[str, str, str]):
        """
        Remove an item from stack
        """
        FILE_STACK.pop(key, None)

    @classmethod
    def push(cls, item: FilePluginItem):
        """
        Push an item to the head of the stack
        """
        key = item.key()
        value = item.value()
        FILE_STACK[key] = value
        FILE_STACK.move_to_end(key, False)

    @classmethod
    def append(cls, item: FilePluginItem):
        """
        Push an item at the end of the stack
        """
        key = item.key()
        value = item.value()
        FILE_STACK[key] = value
        FILE_STACK.move_to_end(key)

    @classmethod
    def get_stack(cls):
        """
        Gets the stack.
        """
        return FILE_STACK

    @classmethod
    def clear(cls):
        FILE_STACK.clear()

    @classmethod
    def clear_project(cls, projectId):
        for key in [k for k in FILE_STACK if k[2] == projectId]:
            FILE_STACK.pop(key, None)

    def get_id(self) -> str:
        return ITEM_TYPE

    def get_plugin_tag(self) -> str:
        return "#open"

    def is_enabled(self) -> bool:
        settings = plugin_settings()
        return dict_deep_get(settings, "plugins.files.enabled", True) is True

    def generate_items(self, projectId):
        details = []
        meta = []
        for key, item in FILE_STACK.items():
            # Skip file if not for the current window
            if key[2] != projectId:
                continue
            file = File(key[0], key[1], key[2])
            details.append({
                "trigger": file.get_file_name(),
                "annotation": "files",
                "kind": KIND_FILE_PLUGIN_FILE_ITEM_TYPE[:2],
            })
            meta.append(file)
        return (details, meta)

    def is_applicable(self, item: sublime.QuickPanelItem):
        return item.kind[2] == ITEM_TYPE

    def on_highlight(self, item: sublime.QuickPanelItem, meta, window: sublime.Window):
        # meta is a File object; fall back to importing from the item if needed
        file = meta if isinstance(meta, File) else File(*item.kind[3])
        window.open_file(file.get_full_path(), sublime.TRANSIENT)

    def on_select(self, item: sublime.QuickPanelItem, meta, window: sublime.Window):
        file = meta if isinstance(meta, File) else File(*item.kind[3])
        window.open_file(file.get_full_path())

    def refresh_cache(self, window: sublime.Window):
        settings = plugin_settings()
        only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)
        enable_cache = dict_deep_get(settings, "plugins.files.enable_cache", False)
        if enable_cache is True:
            return
        if only_show_unopened_files_on_empty_window is True and len(window.sheets()) > 0:
            return
        parse_listed_files(window)


def list_files(directory="."):
    settings = plugin_settings()
    ripgrep = str(settings.get("ripgrep_path", ""))

    if ripgrep == "" or os.path.exists(ripgrep) is False:
        print("⚠ To enable Files plugin in Compass, you need to set the ripgrep path.")
        return None

    command = [settings["ripgrep_path"], "--files", directory]

    try:
        cmdFlags = 0
        if sublime.platform() == "windows":
            cmdFlags = subprocess.CREATE_NO_WINDOW

        # Run the command and capture the output
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # This makes sure the output is treated as text (str) rather than bytes
            creationflags=cmdFlags,
        )

        if result.returncode != 0:
            print(result.stderr)
            return []

        return result.stdout.splitlines()
    except Exception as e:
        print(f"An error occurred: {e}")


def parse_listed_files(window: sublime.Window):
    folders = window.folders()
    projectId = window.project_file_name() or str(window.id())

    for folder in folders:
        files = list_files(folder)
        if files is None:
            continue
        for file in files:
            item = FilePluginItem(File(file, folder, projectId), None)
            CompassPluginFileStack.append(item)
