import sublime
from typing import List, Optional
from .sheet_group import SheetGroup
from .stack import get_stack, push_sheets, remove_sheet

def convert_stack_to_sheet_group(window, group):
    stack = get_stack(window, group) or []
    sheets_stack: List[SheetGroup] = []
    for item in stack:
        sheets = SheetGroup()
        for sheet_id in item[2]:
            sheets.append(sublime.Sheet(sheet_id))
        sheets.set_focused(sublime.Sheet(item[3]))
        sheets_stack.append(sheets)
    return sheets_stack

"""
This is more like Sheet stack
"""
class ViewStack():
    def __init__(self, window: sublime.Window, group: int):
        self.window = window
        self.group = group
        self.stack: List[SheetGroup] = convert_stack_to_sheet_group(window, group)

    def get(self, index: int):
        """
        @deprecated
        """
        if 0 <= index < len(self.stack):
            return self.stack[index]
        return None

    def push(self, window: sublime.Window, sheets: List[sublime.Sheet], group: int = 0, focused: Optional[sublime.Sheet] = None):
        # sheet_group = SheetGroup(sheets)
        push_sheets(window, sheets, group, focused)
        self.stack: List[SheetGroup] = convert_stack_to_sheet_group(window, group)

    def append(self, window: sublime.Window, sheets: List[sublime.Sheet], group: int = 0):
        """
        @deprecated
        """
        self.stack = [item for item in self.stack if item != sheets]
        self.stack.append(SheetGroup(sheets))

    def remove(self, sheet: sublime.Sheet):
        remove_sheet(sheet)
        self.stack: List[SheetGroup] = convert_stack_to_sheet_group(self.window, self.group)

    def clear(self):
        """
        @deprecated
        """
        self.stack = []

    def all(self) -> List[SheetGroup]:
        return self.stack

    def sheet_total(self):
        """
        @deprecated
        """
        total = 0
        for sheets in self.stack:
            total = total + sheets.__len__()
        return total

    def head(self):
        if self.stack.__len__() > 0:
            return self.stack[0]
        return None
