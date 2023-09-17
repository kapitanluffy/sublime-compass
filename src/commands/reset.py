import sublime_plugin
from ...view_stack import ViewStack
from ..stack_manager import StackManager
from .show import CompassShowCommand
from ...utils import plugin_settings, plugin_state

# @note this is glitchy..
class CompassResetCommand(sublime_plugin.WindowCommand):
    def run(self):
        state = plugin_state()
        state["is_reset"] = True

        # @note hide_overlay calls on_done
        self.window.run_command("hide_overlay")
