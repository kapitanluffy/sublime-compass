from typing import List, Union
import sublime

"""
The group of selected sheets in a sublime group
"""
class SheetGroup(List[sublime.Sheet]):
    def __init__(self, *args):
        super().__init__(*args)
        self.focused: Union[sublime.Sheet, None] = self[0] if len(self) > 0 else None

    def set_focused(self, sheet: Union[sublime.Sheet, None]):
        self.focused = sheet

    def get_focused(self):
        return self.focused
