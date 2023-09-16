import sublime_plugin
from ...utils import plugin_settings, plugin_state

class CompassMoveCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        is_forward = kwargs.get('forward', True)
        settings = plugin_settings()
        state = plugin_state()

        if settings["jump_to_most_recent_on_show"] is True and state["highlighted_index"] <= 1 and is_forward is True:
            self.window.run_command("move", { "by": "lines", "forward": False if state["highlighted_index"] == 1 else True })
            return

        self.window.run_command("move", { "by": "lines", "forward": is_forward })
