import sublime
from typing import List
from .sheet_group import SheetGroup

"""
This is more like Sheet stack
"""
class ViewStack():
    def __init__(self, window: sublime.Window, group: int):
        self.window = window
        self.group = group
        self.stack: List[SheetGroup] = []

    def get(self, index: int):
        if 0 <= index < len(self.stack):
            return self.stack[index]
        return None

    def push(self, sheets: List[sublime.Sheet]):
        sheets = SheetGroup(sheets)

        for sheet in sheets:
            for i, sheet_stack in enumerate(self.stack):
                if sheet in sheet_stack:
                    self.stack[i].remove(sheet)

                    # remove if empty
                    if len(self.stack[i]) <= 0:
                        self.stack.pop(i)
                    break

        if len(sheets) == 1:
            sheets.set_focused(sheets[0])

        self.stack.insert(0, sheets)

    def append(self, sheets: List[sublime.Sheet]):
        self.stack = [item for item in self.stack if item != sheets]
        self.stack.append(SheetGroup(sheets))

    def remove(self, sheet: sublime.Sheet):
        for i, sheet_stack in enumerate(self.stack):
            if sheet in sheet_stack:
                self.stack[i].remove(sheet)
                if len(self.stack[i]) <= 0:
                    self.stack.pop(i)
                break

    def clear(self):
        self.stack = []

    def all(self) -> List[SheetGroup]:
        return self.stack

    def sheet_total(self):
        total = 0
        for sheets in self.stack:
            total = total + sheets.__len__()
        return total

    def head(self):
        if self.stack.__len__() > 0:
            return self.stack[0]
        return None

    def _sheet_filter(self, sheet: sublime.Sheet, new_sheet: sublime.Sheet):
        return sheet.id() != new_sheet.id()
