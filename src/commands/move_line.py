import sublime_plugin
from ...utils import plugin_settings, plugin_state

class CompassMoveLineCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        is_forward = kwargs.get('forward', True)
        character = kwargs.get('character', 1)

        if character.isdigit() is False:
            return

        count = int(character)

        if count == 0:
            count = 10

        for c in range(count):
            self.window.run_command("move", { "by": "lines", "forward": is_forward })
