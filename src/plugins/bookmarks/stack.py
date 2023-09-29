from collections import OrderedDict
from typing import List, Optional
from ...sheet_group import SheetGroup
import sublime
import sublime_plugin
import os


BOOKMARK_STACK = OrderedDict()
KIND_BOOKMARK_TYPE = (sublime.KindId.COLOR_ORANGISH, "b", "Bookmark")


class BookmarkStackItem():
    def __init__(
        self,
        window: sublime.Window,
        sheets: List[sublime.Sheet],
        group: int = 0,
        focused: Optional[sublime.Sheet] = None,
        bookmark: Optional[sublime.Region] = None
    ):
        self.window = window
        self.sheets = sheets
        self.group = group
        self.focused = focused
        self.bookmark = bookmark

    def set_bookmark(self, bookmark: sublime.Region):
        self.bookmark = bookmark

    def to_tuple(self):
        bookmark = self.bookmark
        focused = self.focused

        if focused is None:
            focused = self.sheets[0]

        if bookmark is not None:
            bookmark = bookmark.to_tuple()

        sheet_ids = [sheet.id() for sheet in self.sheets]
        item = (self.window.id(), self.group, sheet_ids, focused.id())
        return (bookmark, item)


def get_visible_lines(view: sublime.View, visible_lines, view_selection):
    fallback_line_string = None
    line_strings: List[str] = []
    MAX_SURROUND_LINE_THRESHOLD = 1

    for line_index, line in enumerate(visible_lines):
        line_string = view.substr(line).rstrip()

        if fallback_line_string is None and line_string != "":
            fallback_line_string = line_string

        if line != view_selection:
            continue

        real_line_threshold = MAX_SURROUND_LINE_THRESHOLD + 1
        lines = list(range(line_index-1, line_index-real_line_threshold, -1)) + [line_index] + list(range(line_index+1, line_index+real_line_threshold, 1))

        for preview_line in lines:
            if preview_line < 0 or preview_line >= len(visible_lines):
                continue

            line_string = view.substr(visible_lines[preview_line])
            # @note does not work
            # line_string = replace_spaces_with_spaces(line_string)

            if line_string != "":
                line_strings.append(line_string)

        if line_strings.__len__() > 0:
            return line_strings

    return [fallback_line_string or ""]


def generate_preview(view: sublime.View):
    visible_lines = view.lines(view.visible_region())
    selection = view.sel()

    if len(selection) <= 0:
        return ""

    view_selection = view.line(view.sel()[0].a)
    preview = view.substr(view_selection).strip()

    if preview.__len__() <= 0:
        preview_lines = get_visible_lines(view, visible_lines, view_selection)
        preview = preview_lines[0].lstrip() if preview_lines.__len__() > 0 and preview_lines[0].lstrip() != "" else preview

    # @todo for groups, show the preview for the currently active in that group
    return """<tt style='color:red'>%s</tt>""" % sublime.html.escape(preview)


def guess_sheet_name(sheet: sublime.Sheet):
    name = "Untitled #%s" % sheet.id()
    file_name = sheet.file_name()
    view = sheet.view()

    if file_name:
        name = os.path.basename(file_name)
    elif view is not None and view.name() != "":
        name = view.name()

    return name


class Stack():
    @classmethod
    def get_from_bookmark(cls, bookmark: sublime.Region):
        if bookmark.to_tuple() in BOOKMARK_STACK:
            return bookmark.to_tuple()
        return None

    @classmethod
    def remove_bookmark(cls, region: sublime.Region):
        key = cls.get_from_bookmark(region)
        if key is not None:
            BOOKMARK_STACK.pop(key)
        return key is not None

    @classmethod
    def push(cls, region: sublime.Region, item: BookmarkStackItem):
        cls.remove_bookmark(region)
        item.set_bookmark(region)
        key, bookmark = item.to_tuple()
        BOOKMARK_STACK[key] = bookmark
        BOOKMARK_STACK.move_to_end(key, False)

    @classmethod
    def append(cls, region: sublime.Region, item: BookmarkStackItem):
        cls.remove_bookmark(region)
        item.set_bookmark(region)
        key, bookmark = item.to_tuple()
        BOOKMARK_STACK[key] = bookmark

    @classmethod
    def get_stack(cls):
        return BOOKMARK_STACK


def generate_quickpanel_item(item):
    region, stack_item = item

    tags = '#mark'
    sheet = sublime.Sheet(stack_item[3])
    view = sheet.view()
    preview = generate_preview(view) if view is not None else ''
    sheet_name = guess_sheet_name(sheet)
    kind = (*KIND_BOOKMARK_TYPE, region)
    trigger = "%s | %s" % (tags, sheet_name)
    annotation = 'bookmarks'

    return sublime.QuickPanelItem(trigger=trigger, kind=kind, details=preview, annotation=annotation)


def bookmarks_generate_items():
    meta = []
    items = []
    for key, item in BOOKMARK_STACK.items():
        print(">", key, ">", item)
        items.append(generate_quickpanel_item((key, item)))
        meta.append(SheetGroup([sublime.Sheet(sheet) for sheet in item[2]]))
    return (items, meta)


def bookmarks_handle_selection(window: sublime.Window, sheets: SheetGroup, bookmark: sublime.Region):
    window.select_sheets(sheets)
    focused = sheets.get_focused()

    if len(sheets) > 0 and focused is not None:
        window.focus_sheet(focused)
        view = window.active_view()

        if view is None:
            return

        view.sel().clear()
        view.sel().add(bookmark)
