import sublime

from . import STACK, append_sheets, build_stack, hydrate_stack, get_item, CompassPluginFilesListener


def load_window(window: sublime.Window):
    hydrate_stack(window)

    if len(STACK) != len(window.sheets()):
        for sheet in window.sheets():
            if get_item(sheet) is None:
                append_sheets(window, [sheet])


def load():
    windows = sublime.windows()

    for window in windows:
        sublime.set_timeout_async(lambda: load_window(window))

    CompassPluginFilesListener.on_plugin_loaded()
