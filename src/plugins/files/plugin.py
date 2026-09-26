"""Files (#open) - Compass Navigator bundled plugin."""

from collections import OrderedDict
import os
import threading
import time
from typing import List, Optional, Tuple, OrderedDict as TOrderedDict
import sublime

from ...utils import dict_deep_get, plugin_debug, plugin_settings
from ...events import check_folders_changed
from ...plugins_registry import order_by_recent, recent_keys, record_selection
from ..plugin_base import CompassPlugin
from .utils import _SCAN_IN_FLIGHT, _walk_folders, FilePluginItem

ITEM_TYPE = "compass_plugin_file_open_file"
CompassItemTuple = Tuple[int, int, List[int], int]
FILE_STACK: TOrderedDict[Tuple[str, str, str], Optional[CompassItemTuple]] = OrderedDict()
KIND_FILE_PLUGIN_FILE_ITEM_TYPE = (sublime.KindId.COLOR_YELLOWISH, "f", ITEM_TYPE)


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

    def on_load(self) -> None:
        # Startup scan, one worker per window. Moved from the deleted
        # files/events.py (files_plugin_on_load) — dispatch needs no
        # Sublime listener for this.
        print("CompassNavigator - Files plugin - loaded!")

        settings = plugin_settings()
        only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)
        windows = sublime.windows()
        # @todo watch setting if changed
        for window in windows:
            if only_show_unopened_files_on_empty_window is False or (only_show_unopened_files_on_empty_window is True and window.sheets().__len__() <= 0):
                scan_files_async(window, "startup")

    def on_unload(self) -> None:
        CompassPluginFileStack.clear()

    def on_folders_changed(self, window: sublime.Window) -> None:
        scan_files_async(window, "activated")

    def on_window_closed(self, window: sublime.Window) -> None:
        # Moved from the deleted files/events.py listener — core
        # dispatches window_closed, the plugin forgets the project.
        projectId = window.project_file_name() or str(window.id())
        CompassPluginFileStack.clear_project(projectId)
        plugin_debug("on_window_closed", len(CompassPluginFileStack.get_stack()))

    def on_project_closed(self, window: sublime.Window) -> None:
        # Same as above, for the project-close path.
        projectId = window.project_file_name() or str(window.id())
        CompassPluginFileStack.clear_project(projectId)
        plugin_debug("on_project_closed", len(CompassPluginFileStack.get_stack()))

    def on_project_loaded(self, window: sublime.Window) -> None:
        # Moved from the deleted files/events.py listener. The explicit
        # enabled check stays even though dispatch targets enabled
        # plugins — preserves the exact old behavior.
        settings = plugin_settings()
        is_enabled = dict_deep_get(settings, "plugins.files.enabled", True)
        if is_enabled is False:
            return
        scan_files_async(window, "project-load")

    def generate_items(self, projectId):
        details = []
        meta = []
        keys = [key for key in FILE_STACK if key[2] == projectId]
        recent = set(recent_keys(self.get_id()))
        for key in order_by_recent(self.get_id(), keys):
            # Lightweight meta: a (path, folder, projectId) tuple. The
            # File object is built on demand in on_highlight/on_select,
            # so opening the panel on huge indexes doesn't construct
            # one per row. All rows stay listed and searchable.
            details.append({
                "trigger": os.path.relpath(key[0], key[1]),
                "annotation": "files · recent" if key in recent else "files",
                "kind": KIND_FILE_PLUGIN_FILE_ITEM_TYPE[:2],
            })
            meta.append((key[0], key[1], key[2]))
        return (details, meta)

    def is_applicable(self, item: sublime.QuickPanelItem):
        try:
            return item.kind[2] == ITEM_TYPE
        except Exception:
            return False

    def on_highlight(self, window: sublime.Window, item: sublime.QuickPanelItem, meta):
        if not self.is_applicable(item):
            return
        # meta is a generic payload round-tripped through Compass core;
        # this plugin always sends a (path, folder, projectId) tuple.
        path = meta[0] if isinstance(meta, (tuple, list)) else meta
        window.open_file(path, sublime.TRANSIENT)

    def on_select(self, window: sublime.Window, item: sublime.QuickPanelItem, meta):
        if not self.is_applicable(item):
            return
        # meta is a generic payload round-tripped through Compass core;
        # this plugin always sends a (path, folder, projectId) tuple.
        record_selection(self.get_id(), tuple(meta) if isinstance(meta, list) else meta)
        path = meta[0] if isinstance(meta, (tuple, list)) else meta
        window.open_file(path)

    def refresh_cache(self, window: sublime.Window):
        settings = plugin_settings()
        only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)
        enable_cache = dict_deep_get(settings, "plugins.files.enable_cache", False)
        if enable_cache is True:
            return
        if only_show_unopened_files_on_empty_window is True and len(window.sheets()) > 0:
            return
        try:
            projectId = window.project_file_name() or str(window.id())
        except Exception:
            return
        if projectId in _SCAN_IN_FLIGHT:
            # A worker will populate FILE_STACK; the panel cannot update
            # dynamically, so skip the duplicate walk and show without
            # file rows this time.
            return
        if not check_folders_changed(window):
            return
        parse_listed_files(window)


def parse_listed_files(window: sublime.Window, source="panel"):
    started = time.perf_counter()
    folders = window.folders()
    projectId = window.project_file_name() or str(window.id())

    found = _walk_folders(folders)
    for file, folder in found:
        item = FilePluginItem((file, folder, projectId), None)
        CompassPluginFileStack.append(item)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    plugin_debug(
        "Compass files scan (%s): %d folders, %d files in %dms on %s"
        % (source, len(folders), len(found), elapsed_ms, threading.current_thread().name)
    )


def scan_files_async(window: sublime.Window, source="startup"):
    """
    Walk folders on a worker thread, then apply to FILE_STACK on the
    main thread. Concurrent scans for the same project are deduped.
    """
    try:
        projectId = window.project_file_name() or str(window.id())
        folders = tuple(window.folders())
    except Exception:
        return
    if projectId in _SCAN_IN_FLIGHT:
        return
    _SCAN_IN_FLIGHT.add(projectId)

    def walk():
        started = time.perf_counter()
        found = []
        try:
            found = _walk_folders(folders)
        finally:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            sublime.set_timeout(
                lambda: _apply_scan(window, projectId, folders, found, elapsed_ms, source)
            )

    sublime.set_timeout_async(walk)


def _apply_scan(window, projectId, folders, found, elapsed_ms, source):
    _SCAN_IN_FLIGHT.discard(projectId)
    try:
        current = tuple(window.folders())
    except Exception:
        return
    if current != folders:
        # Folders moved under us; leave the snapshot stale so the next
        # panel open re-scans instead of applying stale rows.
        return
    CompassPluginFileStack.clear_project(projectId)
    for file, folder in found:
        item = FilePluginItem((file, folder, projectId), None)
        CompassPluginFileStack.append(item)
    check_folders_changed(window)
    plugin_debug(
        "Compass files scan (async, %s): %d folders, %d files in %dms"
        % (source, len(folders), len(found), elapsed_ms)
    )


_PLUGIN_INSTANCE = CompassPluginFileStack()
