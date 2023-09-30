from typing import List, Union
import sublime
import sublime_plugin
from ...utils import plugin_settings, plugin_state
from .. import File, ViewStack, SheetGroup
from ..utils import parse_listed_files, parse_sheet
import os

KIND_FILE_OPEN = (sublime.KindId.COLOR_YELLOWISH, "f", "OpenFile")


def generate_post_file_item(window: sublime.Window, file_label, tags, kind, annotation):
    settings = plugin_settings()
    open_folders = window.folders()
    is_tags_enabled = settings.get("enable_tags")

    for folder in open_folders:
        file_label = file_label.replace("%s%s" % (folder, os.path.sep), "")

    if is_tags_enabled is True and len(tags) > 0:
        file_label = "%s%s%s" % (' '.join(tags), ' | ', file_label)

    return sublime.QuickPanelItem(trigger=file_label, kind=kind, annotation=annotation)


class CompassShowCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        settings = plugin_settings()
        state = plugin_state()

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

            trigger = ' + '.join(names)
            is_tags_enabled = settings.get('enable_tags', False)
            annotation = ' '.join(tags) if is_tags_enabled else ''
            item = sublime.QuickPanelItem(trigger=trigger, kind=kind, details=preview, annotation=annotation)
            items.append(item)
            items_meta.append(sheets)

            for index, file in enumerate(files):
                item = generate_post_file_item(self.window, file or names[index], tags, kind, trigger)
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
                trigger = "#open > %s" % (filename)
                item = sublime.QuickPanelItem(trigger=trigger, kind=KIND_FILE_OPEN)
                unopened_files_items.append(item)
                unopened_files_meta.append(file)

        items = items + post_list + unopened_files_items + file_types_items
        items_meta = items_meta + post_list_meta + unopened_files_meta + file_types_meta

        if len(items) <= 0 or len(items_meta) <= 0:
            return

        state["is_quick_panel_open"] = True
        state["highlighted_index"] = selected_index

        self.window.show_quick_panel(
            items=items,
            selected_index=selected_index,
            on_select=lambda index: self.on_done(index, items, stack, initial_selection, items_meta),
            on_highlight=lambda index: self.on_highlight(index, items, stack, initial_selection, items_meta)
        )

    def on_highlight(self, index: int, items, stack: ViewStack, selection, items_meta: List[Union[SheetGroup, File]]):
        if index == -1:
            raise Exception("Cannot highlight index: -1")

        settings = plugin_settings()
        sheets = items_meta[index]
        state = plugin_state()
        state["highlighted_index"] = index

        is_preview_on_highlight = settings.get("preview_on_highlight", True)

        if is_preview_on_highlight is False:
            state["is_quick_panel_open"] = False
            return

        if isinstance(sheets, File) and sheets is not None:
            state["is_quick_panel_open"] = False
            self.window.open_file(sheets.get_full_path(), sublime.TRANSIENT)

        if isinstance(sheets, SheetGroup) and sheets is not None:
            state["is_quick_panel_open"] = False
            self.window.select_sheets(sheets)

    def on_done(self, index, items, stack: ViewStack, selection, items_meta: List[Union[SheetGroup, File]]):
        state = plugin_state()

        if index == -1:
            index = state["highlighted_index"]

        if state["is_reset"] is True:
            index = 0
            state["is_reset"] = False

        sheets = items_meta[index]

        class_name = type(sheets).__name__
        item_type = items[index].kind[2]
        sub_commands = ["OpenFile", "FileType"]
        is_file = item_type in sub_commands and class_name == "File"

        if sheets is not None and (isinstance(sheets, File) or is_file is True):
            state["is_quick_panel_open"] = False
            assert isinstance(sheets, File)
            self.window.open_file(sheets.get_full_path())
            return

        # @todo on plugin reload, sheets are still SheetGroup because it is a subclass of List.
        if isinstance(sheets, SheetGroup) and sheets is not None:
            state["is_quick_panel_open"] = False
            self.window.select_sheets(sheets)

            # refocus on the selected sheet
            focused = sheets.get_focused()
            if len(sheets) > 0 and focused is not None:
                self.window.focus_sheet(focused)
            return
