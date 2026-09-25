import sublime
import sublime_plugin
from typing import Dict, Tuple
from ..utils import *
from .event_bus import emit
from .stack import cache_stack, hydrate_stack, remove_window
from .view_stack import ViewStack


_FOLDER_SNAPSHOTS: Dict[str, Tuple[str, ...]] = {}


def check_folders_changed(window: sublime.Window) -> bool:
    """
    Window-level folder-list snapshot owned by core. Records the current
    folders and emits compass_folders_changed on delta; any plugin may
    subscribe. Cheap string compare, no ripgrep walk; safe on any thread.
    """
    try:
        projectId = window.project_file_name() or str(window.id())
        current = tuple(window.folders())
    except Exception:
        return False
    previous = _FOLDER_SNAPSHOTS.get(projectId)
    _FOLDER_SNAPSHOTS[projectId] = current
    if previous is None or previous != current:
        emit("compass_folders_changed", window=window)
        return True
    return False


def should_skip_view(view):
    return view.element() is not None and view.element() != "find_in_files:output"


# Discard the most unused item if max_open_tabs is met
def cleanup_sheets(stack: ViewStack):
    settings = plugin_settings()
    max_open_tabs = settings.get('max_open_tabs', 100)  # type: int

    if max_open_tabs == 0 or stack.length() <= max_open_tabs:
        return True

    stack_length = stack.length()

    for si in range(stack_length):
        index = stack_length - (si + 1)
        last_sheet_group = stack.all()[index]

        for s in last_sheet_group:
            sview = s.view()

            if sview is None:
                continue

            if sview.is_dirty() or sview.is_scratch():
                continue

            print("cleaning up", sview.file_name() or sview.name())

            s.close()
            return True


class CompassFocusListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "compass" and operator == 0 and operand is True:
            return True
        return False

    def on_load_project_async(self, window):
        hydrate_stack(window)

    def on_pre_close_window(self, window: sublime.Window):
        remove_window(window)

    def on_pre_close_project(self, window: sublime.Window):
        remove_window(window)

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

        group = sheet.group() or window.active_group()
        stack = ViewStack(window, group)
        stack.remove(sheet)

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

        # Browsing previews fire activations too — they must not rewrite
        # MRU history (or auto-close previewed tabs via cleanup_sheets).
        # The genuine selection pushes on close, after on_done clears
        # is_quick_panel_open.
        if plugin_state()["is_quick_panel_open"] is True:
            return

        group = sheet.group() or window.active_group()
        stack = ViewStack(window, group)
        sheets = window.selected_sheets_in_group(group)
        stack.push(window, sheets, group, sheet)
        cleanup_sheets(stack)
        cache_stack(window)
