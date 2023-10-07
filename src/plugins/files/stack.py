from collections import OrderedDict
import subprocess
from typing import List, Optional, Tuple, OrderedDict as TOrderedDict
import sublime
from .file import File

ITEM_TYPE = "compass_plugin_file_open_file"
CompassItemTuple = Tuple[int, int, List[int], int]
FILE_STACK: TOrderedDict[Tuple[str, str], Optional[CompassItemTuple]] = OrderedDict()
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
        return (file, folder)

    def value(self):
        item = self.item.to_tuple() if self.item is not None else None
        return item


class CompassPluginFileStack():
    @classmethod
    def get(cls, key: Tuple[str, str]):
        """
        Get an item from stack
        """
        if key in FILE_STACK:
            return FILE_STACK[key]
        return None

    @classmethod
    def remove(cls, key: Tuple[str, str]):
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
    def generate_quickpanel_item(cls, key: Tuple[str, str], item):
        file = File(key[0], key[1])

        tags = '#open'
        annotation = 'files'
        kind = (*KIND_FILE_PLUGIN_FILE_ITEM_TYPE, key)
        trigger = "%s | %s" % (tags, file.get_file_name())
        return sublime.QuickPanelItem(trigger=trigger, kind=kind, annotation=annotation)

    @classmethod
    def generate_items(cls):
        meta = []
        items = []
        for key, item in FILE_STACK.items():
            file = File(key[0], key[1])
            items.append(cls.generate_quickpanel_item(key, item))
            meta.append(file)
        return (items, meta)

    @classmethod
    def is_applicable(cls, item: sublime.QuickPanelItem):
        return item.kind[2] == ITEM_TYPE

    @classmethod
    def on_highlight(cls, item: sublime.QuickPanelItem, window: sublime.Window):
        key: Tuple[str, str] = item.kind[3]
        file = File(*key)
        window.open_file(file.get_full_path(), sublime.TRANSIENT)

    @classmethod
    def on_select(cls, item: sublime.QuickPanelItem, window: sublime.Window):
        key: Tuple[str, str] = item.kind[3]
        file = File(*key)
        window.open_file(file.get_full_path())


def list_files(directory="."):
    command = ["d:\\~\\bin\\ripgrep\\rg.exe", "--files", directory]

    try:
        # Run the command and capture the output
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # This makes sure the output is treated as text (str) rather than bytes
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode != 0:
            print(result.stderr)
            return []

        return result.stdout.splitlines()
    except Exception as e:
        print(f"An error occurred: {e}")


def parse_listed_files(window: sublime.Window):
    folders = window.folders()
    for folder in folders:
        files = list_files(folder)
        if files is None:
            return None
        for file in files:
            item = FilePluginItem(File(file, folder), None)
            CompassPluginFileStack.append(item)
