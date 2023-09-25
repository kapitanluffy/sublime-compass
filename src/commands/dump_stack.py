from ..stack import STACK
import sublime_plugin

class CompassDumpStackCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        window_stack = list(filter(lambda block: block[0] == self.window.id(), STACK))
        print("STACK>", window_stack, len(window_stack))
