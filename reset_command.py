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
