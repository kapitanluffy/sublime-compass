import sublime
from . import STACK, append_sheets, build_stack, hydrate_stack, get_item


def load_window(window: sublime.Window):
    is_hydrated = hydrate_stack(window)

    if len(STACK) != len(window.sheets()):
        for sheet in window.sheets():
            if get_item(sheet) is None:
                append_sheets(window, [sheet])

    if is_hydrated is False:
        build_stack(window)


def load():
    windows = sublime.windows()

    for window in windows:
        sublime.set_timeout_async(lambda: load_window(window))
