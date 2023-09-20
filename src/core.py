import sublime
from . import build_stack

def load_window(window: sublime.Window):
    build_stack(window)

def load():
    windows = sublime.windows()

    for window in windows:
        load_window(window)
