from ..core import load
import sublime
import sublime_plugin

class CompassIndexFilesCommand(sublime_plugin.WindowCommand):
    def run_index(self):
        print("Reindexing files...")
        self.window.run_command('compass_clear_cache')
        load()

    def run(self, **kwargs):
        sublime.set_timeout_async(self.run_index)
