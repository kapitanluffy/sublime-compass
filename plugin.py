import os
import sublime
import sublime_plugin
from .stack_manager import StackManager
from .build_stack_command import ContextKeeperBuildStackCommand
from .utils import *
from typing import List

# Build the stack from window object
def build_stack(window):
    sheets = window.sheets()

    for sheet in sheets:
        group = sheet.group()
        stack = StackManager.get(window, group)
        stack.push([sheet])

def plugin_loaded():
    reset_plugin_state()
    build_stack(sublime.active_window())

def plugin_unloaded():
    # remove all stacks when unloading
    StackManager.clear()

def is_view_valid_tab(view):
    return view.element() is not None and view.element() != "find_in_files:output"

class ContextKeeperFocusListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "context_keeper" and operator == 0 and operand is True:
            return True
        return None

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

        plugin_debug("closing view ", view)

        if is_view_valid_tab(view):
            return

        window = view.window()
        sheet = view.sheet()

        if window is None:
            plugin_debug("Window for View #%s is gone" % view.id())
            return

        if sheet is None:
            plugin_debug("Sheet for View #%s is gone" % view.id())
            return

        window.run_command("context_keeper_close")

        group = window.active_group()
        stack = StackManager.get(window, group)
        stack.remove(sheet)

    def on_activated_async(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is not None and sheet.is_transient():
            return

        if ContextKeeperBuildStackCommand.is_building is True:
            return

        if is_view_valid_tab(view):
            return

        window = view.window()

        if window is None:
            plugin_debug("Window for View #%s is a None xxx" % view.id())
            return

        if window.views().__len__() <= 0:
            return

        group = window.active_group()
        stack = StackManager.get(window, group)
        sheets = window.selected_sheets()

        if stack.sheet_total() == 0:
            return

        # skip pushing to sheet if selected sheet is only one and is already focused
        if view.sheet() in stack.head() and stack.head().__len__() == 1:
            return

        stack.push(sheets)


class ContextKeeperMoveCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        is_forward = kwargs.get('forward', True)
        settings = plugin_settings()
        state = plugin_state()

        if settings["jump_to_most_recent_on_show"] is True and state["highlighted_index"] <= 1 and is_forward is True:
            self.window.run_command("move", { "by": "lines", "forward": False if state["highlighted_index"] == 1 else True })
            return

        self.window.run_command("move", { "by": "lines", "forward": is_forward })


class ContextKeeperCloseCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()

        if view is None:
            return

        sheet = view.sheet()

        if sheet is None:
            return

        # @note experimenting on including unopened files
        # file_name = view.file_name()

        # if sheet.is_transient():
            # self.window.promote_sheet(sheet)
            # view = self.window.open_file(file_name)
            # self.window.focus_view(view)
            # print("z", view, view.sheet(), sheet, sheet.is_transient(), view.is_valid())
            # self.focus_transient_sheet(sheet, view)
            # sublime.set_timeout_async(lambda s=sheet, v=view: self.focus_transient_sheet(sheet, view), 100)

        self.window.run_command("hide_overlay")

    # def focus_transient_sheet(self, sheet, view):
        # self.window.promote_sheet(sheet)
        # self.window.select_sheets([sheet])
        # self.window.focus_view(view)
        # print("zz", view, view.sheet(), sheet)


class ContextKeeperListFilesCommand(sublime_plugin.WindowCommand):
    def run(self):
        folders = self.window.folders()
        for root, dirs, files in os.walk(folders[0]):
            for file in files:
                print(os.path.join(root, file))

