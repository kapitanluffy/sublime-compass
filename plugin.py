import sublime
from .src.stack_manager import StackManager
from .utils import *
from .src import build_stack

def plugin_loaded():
    reset_plugin_state()
    build_stack(sublime.active_window())

def plugin_unloaded():
    # remove all stacks when unloading
    StackManager.clear()
