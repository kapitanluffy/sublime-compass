import sublime
import sublime_plugin

## @expiremental Rewinds your cursor position and slowly replays it back for you
class CompassRewindCommand(sublime_plugin.WindowCommand):
    STEPS = 10

    def run(self):
        for i in range(self.STEPS):
            self.window.active_view().run_command('jump_back')

        for i in range(self.STEPS):
            sublime.set_timeout_async(lambda: self.forward(), 1250 * (i+1))

    def rewind(self):
        self.window.active_view().run_command('jump_back')

    def forward(self):
        self.window.active_view().run_command('jump_forward')
