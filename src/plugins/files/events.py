from typing import List
from .stack import CompassPluginFileStack, parse_listed_files
import sublime
import sublime_plugin


class CompassPluginFilesListener(sublime_plugin.EventListener):
    @classmethod
    def on_plugin_loaded(cls):
        print("CompassNavigator loaded!")
        settings = sublime.load_settings("Compass Navigator.sublime-settings")
        only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)
        windows = sublime.windows()
        # @todo watch setting if changed
        for window in windows:
            if only_show_unopened_files_on_empty_window is False or (only_show_unopened_files_on_empty_window is True and window.sheets().__len__() <= 0):
                parse_listed_files(window)

    def on_init(self, views: List[sublime.View]):
        print("plugin init!")

    def on_pre_close_window(self, window: sublime.Window):
        CompassPluginFileStack.clear()
        print("on_pre_close_window", CompassPluginFileStack.get_stack().__len__())

    def on_pre_close_project(self, window: sublime.Window):
        CompassPluginFileStack.clear()
        print("on_pre_close_project", CompassPluginFileStack.get_stack().__len__())

    def on_load_project_async(self, window):
        CompassPluginFilesListener.on_plugin_loaded()

    # @todo add ability to detect newly added folders
    # @bug compass not working on non-project windows with folders
