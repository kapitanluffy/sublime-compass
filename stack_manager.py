import sublime
from .view_stack import ViewStack

class StackManager():
    stack = []

    @staticmethod
    def _stack_filter(stack: ViewStack, new_stack: ViewStack):
        return stack.window != new_stack.window and stack.group != new_stack.group

    @classmethod
    def add(cls, stack: ViewStack):
        cls.stack = list(filter(lambda i: cls._stack_filter(i, stack), cls.stack))
        cls.stack.append(stack)

    @classmethod
    def get(cls, window: sublime.Window, group = None) -> ViewStack:
        stack = None

        if group is None:
            group = window.active_group()

        for s in cls.stack:
            if s.window == window and s.group == group:
                stack = s
                break

        if stack is None:
            stack = ViewStack(window, group)
            cls.stack.append(stack)

        return stack

    @classmethod
    def remove(cls, stack: ViewStack):
        for i, s in enumerate(cls.stack):
            if stack.window == s.window and stack.group == s.group:
                cls.stack.pop(i)

    @classmethod
    def clear(cls):
        cls.stack = []

    @classmethod
    def all(cls):
        return cls.stack
