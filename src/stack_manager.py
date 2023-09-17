from typing import Dict, Tuple
import sublime
from .view_stack import ViewStack

class StackManager():
    stack: Dict[Tuple[int, int], ViewStack] = {}

    @staticmethod
    def get(window: sublime.Window, group = None) -> ViewStack:
        stack = None

        if group is None:
            group = window.active_group()

        key = (window.id(), group)

        if key in StackManager.stack:
            stack = StackManager.stack[key]

        if stack is None:
            stack = ViewStack(window, group)
            StackManager.stack[key] = stack

        return stack

    @staticmethod
    def remove(stack: ViewStack):
        key = (stack.window.id(), stack.group)
        StackManager.stack.pop(key)

    @staticmethod
    def clear():
        StackManager.stack = {}
