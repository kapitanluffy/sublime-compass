import sublime
from typing import List, Union
from .stack_manager import StackManager
from os import path

STACK = []

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

def remove_sheet(sheet: sublime.Sheet):
    window = sheet.window()
    group = sheet.group()

    window_id = 0
    if window is not None:
        window_id = window.id()

    item = (window_id, group, [sheet.id()])

    if item in STACK:
        STACK.remove(item)
        return

    for block in STACK:
        if sheet.id() in block[2]:
            STACK.remove(block)
            return

def get_item(sheet: sublime.Sheet):
    window = sheet.window()
    group = sheet.group()

    window_id = 0
    if window is not None:
        window_id = window.id()

    item = (window_id, group, [sheet.id()])

    if item in STACK:
        index = STACK.index(item)
        return STACK[index]

    for block in STACK:
        if sheet.id() in block[2]:
            return block

    return None

def append_sheet(sheet: sublime.Sheet):
    window = sheet.window()
    group = sheet.group()
    view = sheet.view()

    if window is None or group is None or view is None:
        return False

    STACK.append((window.id(), group, [sheet.id()]))
    return True

def push_sheets(window: sublime.Window, group: int, sheets: List[sublime.Sheet]):
    sheet_ids = []
    window_id = window.id()

    for sheet in sheets:
        remove_sheet(sheet)
        sheet_ids.append(sheet.id())
    STACK.insert(0, (window_id, group, sheet_ids))

def append_sheets(window: sublime.Window, group: int, sheets: List[sublime.Sheet]):
    sheet_ids = []
    window_id = window.id()

    for sheet in sheets:
        remove_sheet(sheet)
        sheet_ids.append(sheet.id())
    STACK.append((window_id, group, sheet_ids))

def cache_stack(window: sublime.Window):
    window_settings = window.settings()
    project_stack = list(filter(lambda block: block[0] == window.id(), STACK))
    project_stack = []
    for block in STACK:
        if block[0] != window.id():
            continue

        sheet_files = []
        for sheet_id in block[2]:
            sheet = sublime.Sheet(sheet_id)
            sheet_files.append(get_sheet_name(sheet))
        project_stack.append((block[0], block[1], block[2], sheet_files))

    window_settings.set('compass_stack_cache', project_stack)

def get_sheet_from_window(sheet_name: str, window: sublime.Window):
    sheets = window.sheets()
    for sheet in sheets:
        view = sheet.view()
        if view is None:
            continue
        if view.name() == sheet_name:
            return sheet

def get_sheet_from_filepath(file_path: str, window: sublime.Window):
    open_file: Union[sublime.View, None] = window.find_open_file(file_path)
    if open_file is None:
        return None
    return open_file.sheet()

def hydrate_stack(window):
    window_settings = window.settings()
    stack_cache = window_settings.get('compass_stack_cache', [])

    if len(stack_cache) <= 0:
        return False;

    for cache_item in stack_cache:
        sheet_ids = cache_item[2]
        sheet_window = None
        group = None
        sheets = []

        for index, sheet_id in enumerate(sheet_ids):
            sheet = sublime.Sheet(sheet_id)
            sheet_window = sheet.window()
            view = sheet.view()
            group = sheet.group()

            if sheet_window is None or view is None or group is None:
                sheet = None
                file_name = cache_item[3][index]

                if path.exists(file_name) is False:
                    sheet = get_sheet_from_window(file_name, window)

                if path.exists(file_name) is True:
                    sheet = get_sheet_from_filepath(file_name, window)

                if sheet is None:
                    print("Sheet invalid2", cache_item)
                    continue

                sheet_window = sheet.window()
                group = sheet.group()

            sheets.append(sheet)

        if sheet_window is None or group is None:
            print("Cache item invalid", cache_item)
            continue

        stack = StackManager.get(sheet_window, group)
        stack.append(sheets)
        append_sheets(sheet_window, group, sheets)

    return True
