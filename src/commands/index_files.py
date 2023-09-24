import time
from ..utils import generate_files
from ..stack import STACK
import sublime
import sublime_plugin

class CompassIndexFilesCommand(sublime_plugin.WindowCommand):
    def run_index(self):
        print("indexing!")
        for file in generate_files(self.window):
            sublime.set_timeout_async(lambda f=file: print(f.get_file_name()))

    def run(self, **kwargs):
        sublime.set_timeout_async(self.run_index)
