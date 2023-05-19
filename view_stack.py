import sublime
from typing import List


class ViewStack():
    def __init__(self, window: sublime.Window, group: int):
        self.window = window
        self.group = group
        self.stack = []

    def get(self, index):
        if 0 <= index < len(self.stack):
            return self.stack[index]

        return None
        print("not in stack!", index)


    def push(self, sheets: List[sublime.Sheet]):
        for sheet in sheets:
            for i, sheet_stack in enumerate(self.stack):
                if sheet in sheet_stack:
                    self.stack[i].remove(sheet)
                    if len(self.stack[i]) <= 0:
                        self.stack.pop(i)
                    break

        self.stack.insert(0, sheets)

    def append(self, sheets: List[sublime.Sheet]):
        self.stack = [item for item in self.stack if item != sheets]
        self.stack.append(sheets)

    def remove(self, sheet: sublime.Sheet):
        for i, sheet_stack in enumerate(self.stack):
            if sheet in sheet_stack:
                self.stack[i].remove(sheet)
                if len(self.stack[i]) <= 0:
                    self.stack.pop(i)
                break

    def clear(self):
        self.stack = []

    def all(self) -> List[List[sublime.Sheet]]:
        return self.stack

    def sheet_total(self):
        total = 0
        for sheets in self.stack:
            total = total + sheets.__len__()
        return total

    def head(self):
        if self.stack.__len__() > 0:
            return self.stack[0]
        return []

    def _sheet_filter(self, sheet: sublime.Sheet, new_sheet: sublime.Sheet):
        return sheet.id() != new_sheet.id()
