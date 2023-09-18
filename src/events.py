import sublime
import sublime_plugin
from .stack_manager import StackManager
from .commands.build_stack import CompassBuildStackCommand
from ..utils import *
from typing import List

# Build the stack from window object
def build_stack(window):
    sheets = window.sheets()

    for sheet in sheets:
        group = sheet.group()
        stack = StackManager.get(window, group)
        stack.push([sheet])

def is_view_valid_tab(view):
    return view.element() is not None and view.element() != "find_in_files:output"

class CompassFocusListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "compass" and operator == 0 and operand is True:
            return True
        return False

    def on_load_project_async(self, window):
        build_stack(window)

    def on_init(self, views: List[sublime.View]):
        for view in views:
            window = view.window()
            if window is not None:
                build_stack(window)

    def on_pre_close_window(self, window: sublime.Window):
        group = window.active_group()
        stack = StackManager.get(window, group)
        StackManager.remove(stack)

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
        sheet = view.sheet()

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

        group = window.active_group()
        stack = StackManager.get(window, group)
        sheets = window.selected_sheets_in_group(group)

        # skip pushing to sheets if current it is already current sheet group
        head = stack.head()

        if head is not None and view.sheet() in head:
            # set the focused sheet if there are more than 1 sheet selected
            if len(head) > 1:
                head.set_focused(view.sheet())
            return

        stack.push(sheets)

    def on_load(self, view: sublime.View):
        self.on_activated_async(view)