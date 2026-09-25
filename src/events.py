import sublime
import sublime_plugin
from typing import Dict, Tuple
from ..utils import *
from .plugins_registry import dispatch_event


_FOLDER_SNAPSHOTS: Dict[str, Tuple[str, ...]] = {}


def check_folders_changed(window: sublime.Window) -> bool:
    """
    Window-level folder-list snapshot owned by core. Records the current
    folders and broadcasts folders_changed on delta. Cheap string
    compare, no ripgrep walk; safe on any thread.
    """
    try:
        projectId = window.project_file_name() or str(window.id())
        current = tuple(window.folders())
    except Exception:
        return False
    previous = _FOLDER_SNAPSHOTS.get(projectId)
    _FOLDER_SNAPSHOTS[projectId] = current
    if previous is None or previous != current:
        dispatch_event(window, "folders_changed")
        return True
    return False


def should_skip_view(view):
    return view.element() is not None and view.element() != "find_in_files:output"


class CompassFocusListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "compass" and operator == 0 and operand is True:
            return True
        return False

    def on_load_project_async(self, window):
        # Tracking (STACK hydrate) lives in the MRU plugin.
        dispatch_event(window, "project_loaded")

    def on_pre_close_window(self, window: sublime.Window):
        dispatch_event(window, "window_closed")

    def on_pre_close_project(self, window: sublime.Window):
        dispatch_event(window, "project_closed")

    def on_pre_close(self, view: sublime.View):
        state = plugin_state()
        sheet = view.sheet()

        if sheet is None:
            return

        if should_skip_view(view):
            return

        window = view.window()

        if window is None:
            # plugin_debug("Window for View #%s is gone" % view.id())
            return

        if sheet.is_transient():
            return

        dispatch_event(window, "sheet_closed", sheet=sheet)

        if state["is_quick_panel_open"] is True:
            window.run_command("compass_close", {"reset": True})

    def on_activated_async(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is None or sheet.is_transient():
            return

        if should_skip_view(view):
            return

        window = view.window()

        if window is None:
            # plugin_debug("Window for View #%s is a None xxx" % view.id())
            return

        check_folders_changed(window)

        if window.views().__len__() <= 0:
            return

        # Previews fire activations too — they must not rewrite history.
        # The genuine selection pushes on close, after on_done clears
        # is_quick_panel_open.
        if plugin_state()["is_quick_panel_open"] is True:
            return

        group = sheet.group() or window.active_group()
        dispatch_event(window, "sheet_activated", sheet=sheet, group=group)
