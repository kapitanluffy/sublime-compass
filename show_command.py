from typing import List
import sublime
import sublime_plugin
from .utils import plugin_settings, plugin_state
from .view_stack import ViewStack
from .stack_manager import StackManager
import copy
import os
import re
from pathlib import Path

def generate_view_meta(view: sublime.View):
    tags = set()
    kind = sublime.KIND_FUNCTION

    # Set item type
    # Normal sheet
    if view.file_name() is not None and view.element() is None:
        tags.add("#files")

    # Empty sheet
    if view.file_name() is None and view.element() is None:
        tags.add("#empty")
        kind = (sublime.KindId.SNIPPET, "E", "Snippet")

    # Dirty sheets
    if  view.file_name() is not None and view.is_dirty():
        tags.discard('#files')
        tags.add("#dirty")
        kind = (sublime.KindId.VARIABLE, "d", "Type")

    # Find results
    if view.element() == "find_in_files:output":
        tags.add("#search")
        kind = (sublime.KindId.NAMESPACE, "?", "Namespace")

    # Sheets with clones
    if view.is_primary() is True and view.clones().__len__() > 0:
        tags.add("#primary")
        kind = (sublime.KindId.KEYWORD, "P", "Keyword")

    # Sheet clones
    if view.is_primary() is False and view.clones().__len__() > 0:
        tags.add("#clones")
        kind = (sublime.KindId.KEYWORD, "c", "Keyword")

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

class ContextKeeperShowCommand(sublime_plugin.WindowCommand):
    def parseSheet(self, sheet: sublime.Sheet):
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

    def run(self, **kwargs):
        settings = plugin_settings()
        state = plugin_state()

        self.highlighted_index = -1
        is_forward = kwargs.get('forward', True)

        group = self.window.active_group()
        # @todo fix grouping support
        stack = StackManager.get(self.window, group)

        if stack.sheet_total() == 0:
            return

        if self.window.views_in_group(group).__len__() <= 0:
            return

        items = []
        current_view = self.window.active_view_in_group(group)

        if current_view is None:
            raise Exception("Active view is missing!")

        initial_selection = self.window.selected_sheets_in_group(group)
        stack_length = len(stack.all())
        selected_index = 0
        stack_sheets = copy.deepcopy(stack.all())

        if settings["jump_to_most_recent_on_show"] is True:
            selected_index = 1

        if is_forward is False:
            selected_index = stack_length - 1

        postList = []

        for index,sheets in enumerate(stack_sheets):
            names = []
            files = []
            preview = ""
            kind = None
            tags = set()

            for sheet in sheets:
                parsedSheet = self.parseSheet(sheet)

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
            joinedTags = ' '.join(tags)
            item = sublime.QuickPanelItem(trigger=trigger, kind=kind, details=preview, annotation=joinedTags)
            items.append(item)

            file_label: str | None = files[0]

            if file_label is not None:
                open_folders = self.window.folders()

                for folder in open_folders:
                    file_label = file_label.replace("%s%s" % (folder, os.path.sep), "")

            if file_label is None:
                file_label = names[0]

            expandedTrigger = "%s%s%s" % (joinedTags, ' | ', file_label)
            item = sublime.QuickPanelItem(trigger=expandedTrigger, kind=kind, annotation=trigger)
            postList.append(item)

        state["is_quick_panel_open"] = True
        state["highlighted_index"] = selected_index

        self.window.show_quick_panel(
            items=items + postList,
            selected_index=selected_index,
            flags=sublime.QuickPanelFlags.WANT_EVENT,
            on_select=lambda index, event=None: self.on_done(index, items, stack, initial_selection, event),
            on_highlight=lambda index: self.on_highlight(index, items, stack, initial_selection)
        )

    def on_highlight(self, index, items, stack: ViewStack, selection):
        if index == -1:
            raise Exception("Cannot highlight index: -1")

        sheets = stack.get(index)

        if sheets is None and (len(stack.all()) <= index < len(items)):
            self.window.open_file(items[index], sublime.TRANSIENT)

        if sheets is not None:
            self.highlighted_index = index
            self.window.select_sheets(sheets)

        state = plugin_state()
        state["highlighted_index"] = index

        ContextKeeperShowCommand.ignore_highlight=False

    def on_done(self, index, items, stack: ViewStack, selection, event):
        state = plugin_state()

        if index == -1:
            index = self.highlighted_index

        if state["is_reset"] == True:
            index = 0
            state["is_reset"] = False

        sheets = stack.get(index)

        state["is_quick_panel_open"] = False

        if sheets is None and (len(stack.all()) <= index < len(items)):
            print("selected transient!", items[index])
            # self.window.open_file(items[index])
            return

        if sheets is None:
            print("Sheets is missing!")
            return

        self.window.select_sheets(sheets)

        # refocus on the selected sheet
        focused = sheets.get_focused()
        if focused is not None:
            self.window.focus_sheet(focused)
