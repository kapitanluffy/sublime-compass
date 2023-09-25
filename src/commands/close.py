import sublime_plugin
from ...utils import plugin_state

class CompassCloseCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        state = plugin_state()
        state["is_reset"] = kwargs.get("reset", False)

        self.window.run_command("hide_overlay")

