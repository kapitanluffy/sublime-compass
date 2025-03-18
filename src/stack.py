import re
import sublime
from typing import List, Optional, Tuple, Union
from os import path
from time import time

SheetList = List[int]
FocusedSheet = int
Group = int
Window = int

StackItem = List[Tuple[Window, Group, SheetList, FocusedSheet]]
"""
    `StackItem` represents a "view" (not the View object)

    This "view" consists of the following:
        - The active window
        - The active group within the active window
        - The selected sheets within the active group
        - The focused sheet within the selected sheets

    ```py
    Tuple[int, int, List[int], int, Optional[List[str]]]
    #      ^    ^       ^       ^            ^- file paths
    #      |    |       |       |- focused sheet
    #      |    |       |- selected sheets
    #      |    |- group id
    #      |- window id
    ```
"""

STACK: StackItem = []
"""
    `STACK` is the list of StackItems representing the "view"

    The first StackItem in the STACK is the current "view"
"""

STACK_UPDATE_TIME: float = time()

# @todo move to setting
STACK_EXPIRY_TIME: int = 30

def create_item(window: sublime.Window, sheets: List[sublime.Sheet], group: int = 0, focused: Optional[sublime.Sheet] = None):
    if len(sheets) <= 0:
        raise Exception('Cannot create stack item from empty sheets')

    if focused is None:
        focused = sheets[0]

    sheet_ids = [sheet.id() for sheet in sheets]

    return (window.id(), group, sheet_ids, focused.id())

def get_sheet_name(sheet: sublime.Sheet):
    name = "Untitled #%s" % sheet.id()
    file_name = sheet.file_name()
    view = sheet.view()

    if file_name:
        name = file_name
    elif view is not None and view.name() != "":
        name = view.name()
    return name

def remove_window(window: sublime.Window):
    for block in STACK:
       if window.id() == block[0]:
           STACK.remove(block)

def get_head(window: sublime.Window, group: Optional[int] = 0):
    for item in STACK:
        if window.id() == item[0] and group == item[1]:
            return item
    return None

def get_stack(window: sublime.Window, group: Optional[int] = None):
    items: StackItem = []
    for block in STACK:
       if window.id() == block[0] and group is not None and group == block[1]:
            items.append(block)
       if window.id() == block[0] and group is None:
            items.append(block)
    return items

def remove_sheet(sheet: sublime.Sheet):
    item = get_item(sheet)

    if item is not None:
        STACK.remove(item)

    return item is not None

def get_item_index(sheet: sublime.Sheet):
    window = sheet.window()
    group = sheet.group()

    if window is None or group is None:
        return None

    item = create_item(window, [sheet], group)

    if item in STACK:
        return STACK.index(item)

    # look deeper, sheet is in a multi-select sheet
    for index, block in enumerate(STACK):
        if sheet.id() in block[2]:
            return index

    return None

def get_item(sheet: sublime.Sheet):
    index = get_item_index(sheet)
    return STACK[index] if index is not None else None

def push_sheets(window: sublime.Window, sheets: List[sublime.Sheet], group: int = 0, focused: Optional[sublime.Sheet] = None):
    for sheet in sheets:
        remove_sheet(sheet)
    item = create_item(window, sheets, group, focused)
    STACK.insert(0, item)

def append_sheets(window: sublime.Window, sheets: List[sublime.Sheet], group: int = 0, focused: Optional[sublime.Sheet] = None):
    for sheet in sheets:
        remove_sheet(sheet)

    item = create_item(window, sheets, group, focused)
    STACK.append(item)

def cache_stack(window: sublime.Window, force: bool=False):
    global STACK_UPDATE_TIME
    cache_delta = time() - STACK_UPDATE_TIME
    if cache_delta < STACK_EXPIRY_TIME and force is not True:
        return
    STACK_UPDATE_TIME = time()

    window_settings = window.settings()
    stack = []
    for block in STACK:
        if block[0] != window.id():
            continue

        sheet_files = []
        for sheet_id in block[2]:
            sheet = sublime.Sheet(sheet_id)
            sheet_files.append(get_sheet_name(sheet))
        stack.append((block[0], block[1], block[2], block[3], sheet_files))

    window_settings.set('compass_stack_cache', stack)

def get_sheet_from_window(sheet_name: str, sheets: List[sublime.Sheet]):
    for sheet in sheets:
        view = sheet.view()
        if view is None:
            continue
        if view.name() == sheet_name:
            return sheet
        if view.file_name() == sheet_name:
            return sheet
        if view.name() == "" and view.file_name() is None and re.match(r'^Untitled #\d+', sheet_name):
            # @note for now, if view has empty name and file name treat is as "untitled"
            #       in the future, we would want to save identifiers in the view itself to match with the cache
            return sheet

def get_sheet_from_filepath(file_path: str, window: sublime.Window):
    open_file: Union[sublime.View, None] = window.find_open_file(file_path)
    if open_file is None:
        return None
    return open_file.sheet()


# Build the stack from window object
def build_stack(window: sublime.Window):
    sheets = window.sheets()
    groups = window.num_groups()

    for group in range(groups):
        sheets = window.sheets_in_group(group)
        for sheet in sheets:
            append_sheets(window, [sheet], group)


def hydrate_stack(window):
    window_settings = window.settings()
    stack_cache = window_settings.get('compass_stack_cache', [])
    window_sheets = window.sheets()

    if len(stack_cache) <= 0:
        build_stack(window)
        return True

    for cache_item in stack_cache:
        sheet_ids = cache_item[2]
        sheet_window = None
        group = None
        sheets = []
        focused = sublime.Sheet(cache_item[3]) if cache_item is not None else None

        for index, sheet_id in enumerate(sheet_ids):
            sheet = sublime.Sheet(sheet_id)
            sheet_window = sheet.window()
            view = sheet.view()
            group = sheet.group()

            if sheet_window is None or view is None or group is None:
                sheet = None
                file_name = cache_item[4][index]

                if path.exists(file_name) is False:
                    sheet = get_sheet_from_window(file_name, window_sheets)
                    if sheet is not None:
                        window_sheets.remove(sheet)

                if path.exists(file_name) is True:
                    sheet = get_sheet_from_filepath(file_name, window)

                if sheet is None:
                    print("Invalid cache item", cache_item)
                    continue

                sheet_window = sheet.window()
                group = sheet.group()

            sheets.append(sheet)

        if sheet_window is None or group is None:
            continue

        append_sheets(sheet_window, sheets, group, focused)

    return True
