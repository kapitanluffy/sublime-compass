import sublime
import sublime_plugin
from .view_stack import ViewStack
from .stack_manager import StackManager
import copy
from .show_command import ContextKeeperShowCommand
from .utils import plugin_settings, plugin_state

# @note this is glitchy..
class ContextKeeperResetCommand(sublime_plugin.WindowCommand):
    def run(self):
        state = plugin_state()
        state["is_reset"] = True

        # @note hide_overlay calls on_done
        self.window.run_command("hide_overlay")

class ContextKeeperGotoCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        index = kwargs.get('index', 0)

        group = self.window.active_group()
        stack = StackManager.get(self.window, group)

        if stack.sheet_total() == 0:
            raise Exception("stack is empty!")

        current_view = self.window.active_view_in_group(group)

        if current_view is None:
            raise Exception("Active view is missing!")

        selected_sheets = self.window.selected_sheets_in_group(group)
        recently_used = copy.deepcopy(stack.get(index))

        # if the currently selected sheets is equal to the recently used
        # this normally happens when calling this command when the quick panel is shown
        if recently_used == selected_sheets:
            recently_used = copy.deepcopy(stack.get(0))

        print("xxx", recently_used)

        if recently_used is None:
            return

        # ignore highlighted
        ContextKeeperShowCommand.ignore_highlight = True

        self.window.select_sheets(recently_used)
        stack.push(recently_used)

