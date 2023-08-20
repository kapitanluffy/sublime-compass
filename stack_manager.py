from typing import List
import sublime
from .view_stack import ViewStack

class StackManager():
    stack: List[ViewStack] = []

    @staticmethod
    def _stack_filter(stack: ViewStack, new_stack: ViewStack):
        return stack.window != new_stack.window and stack.group != new_stack.group

    @staticmethod
    def add(stack: ViewStack):
        StackManager.stack = list(filter(lambda i: StackManager._stack_filter(i, stack), StackManager.stack))
        StackManager.stack.append(stack)

    @staticmethod
    def get(window: sublime.Window, group = None) -> ViewStack:
        stack = None

        if group is None:
            group = window.active_group()

        for s in StackManager.stack:
            if s.window == window and s.group == group:
                stack = s
                break

        if stack is None:
            stack = ViewStack(window, group)
            StackManager.stack.append(stack)

        return stack

    @staticmethod
    def remove(stack: ViewStack):
        for i, s in enumerate(StackManager.stack):
            if stack.window == s.window and stack.group == s.group:
                StackManager.stack.pop(i)

    @staticmethod
    def clear():
        StackManager.stack = []

    @staticmethod
    def all():
        return StackManager.stack
