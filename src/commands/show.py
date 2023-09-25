from typing import List, Union
import sublime
import sublime_plugin
from ...utils import plugin_settings, plugin_state
from .. import File, ViewStack, SheetGroup
from ..utils import parse_listed_files
import os
import re

KIND_VIEW = (sublime.KindId.COLOR_REDISH, "f", "File")
KIND_VIEW_SCRATCH = (sublime.KindId.COLOR_GREENISH, "s", "Scratch")
KIND_VIEW_DIRTY = (sublime.KindId.COLOR_CYANISH, "d", "Dirty")
KIND_VIEW_FINDFILES = (sublime.KindId.COLOR_BLUISH, "?", "FindFiles")
KIND_VIEW_PRIMARY = (sublime.KindId.COLOR_PINKISH, "P", "PrimaryView")
KIND_VIEW_CLONE = (sublime.KindId.COLOR_PINKISH, "c", "CloneView")
KIND_FILE_OPEN = (sublime.KindId.COLOR_YELLOWISH, "f", "OpenFile")
KIND_FILE_TYPE = (sublime.KindId.COLOR_BLUISH, "t", "FileType")

def generate_view_meta(view: sublime.View):
    tags = set()
    kind = KIND_VIEW

    # Set item type
    # Normal sheet
    if view.file_name() is not None and view.element() is None:
        tags.add("#files")

    # Scratch sheet
    if view.file_name() is None and view.element() is None:
        tags.add("#scratch")
        kind = KIND_VIEW_SCRATCH

    # Dirty sheets
    if  view.file_name() is not None and view.is_dirty():
        tags.discard('#files')
        tags.add("#dirty")
        kind = KIND_VIEW_DIRTY

    # Find results
    if view.element() == "find_in_files:output":
        tags.add("#search")
        kind = KIND_VIEW_FINDFILES

    # Sheets with clones
    if view.is_primary() is True and view.clones().__len__() > 0:
        tags.add("#primary")
        kind = KIND_VIEW_PRIMARY

    # Sheet clones
    if view.is_primary() is False and view.clones().__len__() > 0:
        tags.add("#clones")
        kind = KIND_VIEW_CLONE

    return { "kind": kind, "tags": tags }

def guess_sheet_name(sheet: sublime.Sheet):
    name = "Untitled #%s" % sheet.id()
    file_name = sheet.file_name()
    view = sheet.view()

    if file_name:
        name = os.path.basename(file_name)
    elif view is not None and view.name() != "":
        name = view.name()

    return name

def replace_spaces_with_spaces(text):
    match = re.match(r'^(\s+)', text)
    if match:
        spaces = match.group(1)
        return re.sub(r'^\s+', ' ' * len(spaces), text)
    else:
        return text

# Gets the visible lines surrounding the current line
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
    view_selection = view.line(view.sel()[0].a)
    preview = view.substr(view_selection).strip()

    if preview.__len__() <= 0:
        preview_lines = get_visible_lines(view, visible_lines, view_selection)
        preview = preview_lines[0].lstrip() if preview_lines.__len__() > 0 and preview_lines[0].lstrip() != "" else preview

    # @todo for groups, show the preview for the currently active in that group
    return """<tt style='color:red'>%s</tt>""" % sublime.html.escape(preview)

def parse_sheet(sheet: sublime.Sheet):
    view = sheet.view()

    if view is None or view.is_valid() is False:
        return False

    name = guess_sheet_name(sheet)
    preview = generate_preview(view)
    viewMeta = generate_view_meta(view)
    kind = viewMeta['kind']
    tags = viewMeta['tags']
    file = sheet.file_name()

    return { "name": name, "preview": preview, "kind": kind, "tags": tags, "file": file }

class CompassShowCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        settings = plugin_settings()
        state = plugin_state()

        self.highlighted_index = -1
        is_forward = kwargs.get('forward', True)

        group = self.window.active_group()
        # @todo fix grouping support
        stack = ViewStack(self.window, group)

        # @note show quick panel even if window is empty

        items: List[sublime.QuickPanelItem] = []
        # @note showing quickpanel does not need a current_view

        initial_selection = self.window.selected_sheets_in_group(group)
        stack_length = len(stack.all())
        selected_index = 0
        # stack_sheets = copy.deepcopy(stack.all())
        stack_sheets = stack.all()

        if settings["jump_to_most_recent_on_show"] is True:
            selected_index = 1

        if is_forward is False:
            selected_index = stack_length - 1

        post_list: List[sublime.QuickPanelItem] = []
        items_meta: List[Union[SheetGroup, File]] = []
        post_list_meta: List[SheetGroup] = []

        for index, sheets in enumerate(stack_sheets):
            names = []
            files = []
            preview = ""
            kind = None
            tags = set()

            for sheet in sheets:
                parsedSheet = parse_sheet(sheet)

                if parsedSheet is False:
                    stack.remove(sheet)
                    continue

                names.append(parsedSheet['name'])
                files.append(parsedSheet['file'])
                tags = tags.union(parsedSheet['tags'])

                if preview == "":
                    preview = parsedSheet['preview']

                if kind is None:
                    kind = parsedSheet['kind']

            if names.__len__() <= 0:
                continue

            is_tags_enabled = settings.get("enable_tags")
            trigger = ' + '.join(names)
            joinedTags = ' '.join(tags) if is_tags_enabled else ''
            item = sublime.QuickPanelItem(trigger=trigger, kind=kind, details=preview, annotation=joinedTags)
            items.append(item)
            items_meta.append(sheets)

            file_label: str | None = files[0]

            if file_label is not None:
                open_folders = self.window.folders()

                for folder in open_folders:
                    file_label = file_label.replace("%s%s" % (folder, os.path.sep), "")

            if file_label is None:
                file_label = names[0]

            if is_tags_enabled is True:
                expandedTrigger = "%s%s%s" % (joinedTags, ' | ', file_label)
                item = sublime.QuickPanelItem(trigger=expandedTrigger, kind=kind, annotation=trigger)
                post_list.append(item)
                post_list_meta.append(sheets)

        unopened_files = None
        unopened_files_items: List[sublime.QuickPanelItem] = []
        unopened_files_meta = []
        file_types_items: List[sublime.QuickPanelItem] = []
        file_types_meta = []

        only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)

        if only_show_unopened_files_on_empty_window is False:
            unopened_files = parse_listed_files(self.window)

        if only_show_unopened_files_on_empty_window is True and self.window.sheets().__len__() <= 0:
            unopened_files = parse_listed_files(self.window)

        # @todo refactor and put inside parse_listed_files and maybe rething items+meta
        if unopened_files is not None:
            for file in unopened_files:
                filename = file.get_file_name()
                extension = file.get_extension()[1:]

                trigger = "#open > %s" % (filename)
                item = sublime.QuickPanelItem(trigger=trigger, kind=KIND_FILE_OPEN)
                unopened_files_items.append(item)
                unopened_files_meta.append(file)

                if extension != "":
                    trigger = "#type > %s | %s" % (extension, filename)
                    item = sublime.QuickPanelItem(trigger=trigger, kind=KIND_FILE_TYPE, annotation=filename)
                    file_types_items.append(item)
                    file_types_meta.append(file)

        state["is_quick_panel_open"] = True
        state["highlighted_index"] = selected_index

        items = items + post_list + unopened_files_items + file_types_items
        items_meta = items_meta + post_list_meta + unopened_files_meta + file_types_meta

        if len(items) <= 0 or len(items_meta) <= 0:
            return

        self.window.show_quick_panel(
            items=items,
            selected_index=selected_index,
            on_select=lambda index: self.on_done(index, items, stack, initial_selection, items_meta),
            on_highlight=lambda index: self.on_highlight(index, items, stack, initial_selection, items_meta)
        )

    def on_highlight(self, index: int, items, stack: ViewStack, selection, items_meta: List[Union[SheetGroup, File]]):
        if index == -1:
            raise Exception("Cannot highlight index: -1")

        sheets = items_meta[index]
        self.highlighted_index = index

        if isinstance(sheets, File) and sheets is not None:
            self.window.open_file(sheets.get_full_path(), sublime.TRANSIENT)

        if isinstance(sheets, SheetGroup) and sheets is not None:
            self.window.select_sheets(sheets)

        state = plugin_state()
        state["highlighted_index"] = index

        CompassShowCommand.ignore_highlight=False

    def on_done(self, index, items, stack: ViewStack, selection, items_meta: List[Union[SheetGroup, File]]):
        state = plugin_state()

        if index == -1:
            index = self.highlighted_index

        if state["is_reset"] == True:
            index = 0
            state["is_reset"] = False

        sheets = items_meta[index]

        state["is_quick_panel_open"] = False

        class_name = type(sheets).__name__
        item_type = items[index].kind[2]
        sub_commands = ["OpenFile", "FileType"]
        is_file = item_type in sub_commands and class_name == "File"

        if sheets is not None and (isinstance(sheets, File) or is_file is True):
            assert isinstance(sheets, File)
            self.window.open_file(sheets.get_full_path())
            return

        # @todo on plugin reload, sheets are still SheetGroup because it is a subclass of List.
        if isinstance(sheets, SheetGroup) and sheets is not None:
            self.window.select_sheets(sheets)

            # refocus on the selected sheet
            focused = sheets.get_focused()
            if len(sheets) > 0 and focused is not None:
                self.window.focus_sheet(focused)
            return
