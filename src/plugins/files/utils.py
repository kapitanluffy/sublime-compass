"""Files plugin utilities - Compass Navigator bundled plugin.

Pure helpers and data holders: ripgrep walks plus the FilePluginItem /
CompassItem wrappers. State writes (FILE_STACK) stay in plugin.py with
the class — this module never imports it, so the dependency runs one
way (plugin -> utils, no cycle).
"""

import os
import subprocess
from typing import List, Optional, Tuple
import sublime

from ...utils import plugin_settings

_SCAN_IN_FLIGHT = set()


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


FileKey = Tuple[str, str, str]


class FilePluginItem():
    def __init__(self, key: FileKey, item: Optional[CompassItem]):
        self.key_tuple = key
        self.item = item

    def key(self):
        return self.key_tuple

    def value(self):
        item = self.item.to_tuple() if self.item is not None else None
        return item


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


def _walk_folders(folders):
    """
    Blocking ripgrep walk shared by the sync (panel) and async
    (worker) paths. Returns [(file, folder)] without touching state.
    """
    found = []
    for folder in folders:
        files = list_files(folder)
        if files is None:
            continue
        found.extend((file, folder) for file in files)
    return found
