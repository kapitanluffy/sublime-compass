from typing import List

from ...utils import dict_deep_get, plugin_debug, plugin_settings
from .stack import CompassPluginFileStack, scan_files_async
import sublime
import sublime_plugin


def files_plugin_on_load():
    print("CompassNavigator - Files plugin - loaded!")

    settings = plugin_settings()
    only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)
    windows = sublime.windows()
    # @todo watch setting if changed
    for window in windows:
        if only_show_unopened_files_on_empty_window is False or (only_show_unopened_files_on_empty_window is True and window.sheets().__len__() <= 0):
            scan_files_async(window, "startup")


class CompassPluginFilesListener(sublime_plugin.EventListener):
    def on_init(self, views: List[sublime.View]):
        print("compass plugin - files - init!")

    def on_pre_close_window(self, window: sublime.Window):
        projectId = window.project_file_name() or str(window.id())
        CompassPluginFileStack.clear_project(projectId)
        plugin_debug("on_pre_close_window", len(CompassPluginFileStack.get_stack()))

    def on_pre_close_project(self, window: sublime.Window):
        projectId = window.project_file_name() or str(window.id())
        CompassPluginFileStack.clear_project(projectId)
        plugin_debug("on_pre_close_project", len(CompassPluginFileStack.get_stack()))

    def on_load_project_async(self, window):
        settings = plugin_settings()
        is_enabled = dict_deep_get(settings, "plugins.files.enabled", True)
        if is_enabled is False:
            return
        scan_files_async(window, "project-load")

    # @todo add ability to detect newly added folders
    # @bug compass not working on non-project windows with folders
