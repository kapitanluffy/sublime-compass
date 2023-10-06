from typing import List
from .stack import parse_listed_files
import sublime
import sublime_plugin


# @todo create a way to register these
def plugin_loaded():
    print("plugin loaded!")
    settings = sublime.load_settings("Compass.sublime-settings")
    only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)
    windows = sublime.windows()
    # @todo watch setting if changed
    for window in windows:
        if only_show_unopened_files_on_empty_window is False:
            parse_listed_files(window)
        if only_show_unopened_files_on_empty_window is True and window.sheets().__len__() <= 0:
            parse_listed_files(window)


class CompassFilesPluginListener(sublime_plugin.EventListener):
    def on_init(self, views: List[sublime.View]):
        print("plugin init!")
