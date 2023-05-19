import os
import sublime
import sublime_plugin
from .stack_manager import StackManager
from .build_stack_command import RecentlyUsedExtendedBuildStackCommand
from .utils import *

def plugin_unloaded():
    # remove all stacks when unloading
    StackManager.clear()


class RecentlyUsedExtendedFocusListener(sublime_plugin.EventListener):
    def on_load_project_async(self, window):
        plugin_debug("project loaded! build stack!")
        window.run_command("recently_used_extended_build_stack")

    def on_init(self, views):
        sublime.active_window().run_command("recently_used_extended_build_stack")

    def on_pre_close_window(self, window: sublime.Window):
        group = window.active_group()
        stack = StackManager.get(window, group)

        plugin_debug("closing window, purging stack..", window, group)
        StackManager.remove(stack)

    def on_pre_close(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is not None and sheet.is_transient():
            print("on_pre_close sheet", sheet)
            return

        plugin_debug("closing view ", view)

        if view.element() is not None:
            plugin_debug("View is a %s" % view.element())
            return

        window = view.window()
        sheet = view.sheet()

        if window is None:
            plugin_debug("Window for View #%s is gone" % view.id())
            return

        if sheet is None:
            plugin_debug("Sheet for View #%s is gone" % view.id())
            return

        window.run_command("recently_used_extended_close")

        group = window.active_group()
        stack = StackManager.get(window, group)
        stack.remove(sheet)

    def on_activated_async(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is not None and sheet.is_transient():
            return

        if RecentlyUsedExtendedBuildStackCommand.is_building is True:
            return

        # only work on views with buffer
        if view.element() is not None:
            return

        window = view.window()

        if window is None:
            plugin_debug("Window for View #%s is a None xxx" % view.id())
            return

        # skip stack building if there are no views
        if window.views().__len__() <= 0:
            return

        group = window.active_group()
        stack = StackManager.get(window, group)
        sheets = window.selected_sheets()

        if stack.sheet_total() == 0:
            plugin_debug("new stack! building stack!")
            window.run_command("recently_used_extended_build_stack")
            return

        if view.sheet() in stack.head():
            return

        # plugin_debug("focused!", view, view.sheet(), sheets)
        stack.push(sheets)


class RecentlyUsedExtendedMoveCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        is_forward = kwargs.get('forward', True)
        self.window.run_command("move", { "by": "lines", "forward": is_forward })


class RecentlyUsedExtendedCloseCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()

        if view is None:
            return

        sheet = view.sheet()

        if sheet is None:
            return

        file_name = view.file_name()

        if sheet.is_transient():
            self.window.promote_sheet(sheet)
            # view = self.window.open_file(file_name)
            # self.window.focus_view(view)
            # print("z", view, view.sheet(), sheet, sheet.is_transient(), view.is_valid())
            # self.focus_transient_sheet(sheet, view)
            # sublime.set_timeout_async(lambda s=sheet, v=view: self.focus_transient_sheet(sheet, view), 100)

        self.window.run_command("hide_overlay")

    def focus_transient_sheet(self, sheet, view):
        self.window.promote_sheet(sheet)
        # self.window.select_sheets([sheet])
        # self.window.focus_view(view)
        print("zz", view, view.sheet(), sheet)

    def is_enabled(self) -> bool:
        state = plugin_state()
        return state["is_quick_panel_open"] != False


class RecentlyUsedExtendedKeybindListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "recently_used_extended" and operator == sublime.QueryOperator.EQUAL and operand is True:
            return True

        return False


class RecentlyUsedExtendedListFilesCommand(sublime_plugin.WindowCommand):
    def run(self):
        folders = self.window.folders()
        for root, dirs, files in os.walk(folders[1]):
            for file in files:
                print(os.path.join(root, file))

