import sublime
import sublime_plugin
from .stack_manager import StackManager
from .commands.build_stack import CompassBuildStackCommand
from ..utils import *
from .stack import STACK, append_sheets, cache_stack, hydrate_stack, remove_window

# Build the stack from window object
def build_stack(window: sublime.Window):
    sheets = window.sheets()
    groups = window.num_groups()

    for group in range(groups):
        sheets = window.sheets_in_group(group)
        for sheet in sheets:
            append_sheets(window, [sheet], group)
        StackManager.get(window, group)

def is_view_valid_tab(view):
    return view.element() is not None and view.element() != "find_in_files:output"

class CompassFocusListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "compass" and operator == 0 and operand is True:
            return len(STACK) > 0
        return False

    def on_load_project_async(self, window):
        is_hydrated = hydrate_stack(window)

        if is_hydrated is True:
            groups = window.num_groups()
            for group in range(groups):
                StackManager.get(window, group)

        if is_hydrated is False:
            build_stack(window)

    def on_pre_close_window(self, window: sublime.Window):
        group = window.active_group()
        stack = StackManager.get(window, group)
        StackManager.remove(stack)
        remove_window(window)

    def on_pre_close_project(self, window: sublime.Window):
        group = window.active_group()
        stack = StackManager.get(window, group)
        StackManager.remove(stack)
        remove_window(window)

    def on_pre_close(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is not None and sheet.is_transient():
            return

        if is_view_valid_tab(view):
            return

        window = view.window()
        sheet = view.sheet()

        if window is None:
            # plugin_debug("Window for View #%s is gone" % view.id())
            return

        if sheet is None:
            plugin_debug("Sheet for View #%s is gone" % view.id())
            return

        window.run_command("compass_close")

        group = window.active_group()
        stack = StackManager.get(window, group)
        stack.remove(sheet)

    def on_activated_async(self, view: sublime.View):
        if (len(STACK) <= 0):
            return

        sheet = view.sheet()

        if sheet is None:
            return

        if sheet is not None and sheet.is_transient():
            return

        if CompassBuildStackCommand.is_building is True:
            return

        if is_view_valid_tab(view):
            return

        window = view.window()

        if window is None:
            # plugin_debug("Window for View #%s is a None xxx" % view.id())
            return

        if window.views().__len__() <= 0:
            return

        group = sheet.group() or window.active_group()
        stack = StackManager.get(window, group)
        sheets = window.selected_sheets_in_group(group)
        stack.push(window, sheets, group, sheet)
        cache_stack(window)
