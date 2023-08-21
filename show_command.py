from typing import List
import sublime
import sublime_plugin
from .utils import plugin_settings, plugin_state
from .view_stack import ViewStack
from .stack_manager import StackManager
import copy
import os
import re

class ContextKeeperShowCommand(sublime_plugin.WindowCommand):
    ignore_highlight = False

    def run(self, **kwargs):
        settings = plugin_settings()
        ContextKeeperShowCommand.ignore_highlight = False
        self.highlighted_index = -1
        is_forward = kwargs.get('forward', True)
        state = plugin_state()

        if state["is_quick_panel_open"] is True and settings["jump_to_most_recent_on_show"] is True and state["highlighted_index"] <= 1:
            self.window.run_command("move", { "by": "lines", "forward": False if state["highlighted_index"] == 1 else True })
            return

        if state["is_quick_panel_open"] is True and (settings["jump_to_most_recent_on_show"] is False or state["highlighted_index"] > 1):
            self.window.run_command("move", { "by": "lines", "forward": is_forward })
            return

        group = self.window.active_group()
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

        for index,sheets in enumerate(stack_sheets):
            names = []
            annotation = "#%s" % (index + 1)
            preview = ""
            kind = sublime.KIND_FUNCTION
            tags = set()

            for sheet in sheets:
                view = sheet.view()

                if view is None or view.is_valid() is False:
                    stack.remove(sheet)
                    continue

                name = "Untitled #%s" % sheet.id()
                file_name = sheet.file_name()

                if file_name:
                    name = os.path.basename(file_name)
                elif view.name() != "":
                    name = view.name()

                names.append(name)

                # Get preview of current line
                if preview == "":
                    visible_lines = view.lines(view.visible_region())
                    view_selection = view.line(view.sel()[0].a)
                    preview = view.substr(view_selection).strip()

                    if preview.__len__() <= 0:
                        preview_lines = self.get_visible_lines(view, visible_lines, view_selection)
                        preview = preview_lines[0].lstrip() if preview_lines.__len__() > 0 and preview_lines[0].lstrip() != "" else preview

                    # @todo for groups, show the preview for the currently active in that group
                    preview = """<tt style='color:red'>%s</tt>""" % sublime.html.escape(preview)

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

            if names.__len__() <= 0:
                continue

            trigger = ', '.join(names)

            # @todo hacky tags for filter
            # spaces = [' '] * 10
            # spaces = ''.join(spaces)
            # trigger = "%s%s%s" % (trigger, spaces, ' '.join(tags))
            # annotation = ' '.join(tags)
            annotation = ""

            item = sublime.QuickPanelItem(trigger=trigger, annotation=annotation, kind=kind, details=preview)
            items.append(item)

        # @note planning to include existing files in the folder
        # folders = self.window.folders()
        # for folder in folders:
        #     for root, dirs, files in os.walk(folder):
        #         for file in files:
        #             items.append(os.path.join(root, file))

        state["is_quick_panel_open"] = True
        state["highlighted_index"] = selected_index

        self.window.show_quick_panel(
            items=items,
            selected_index=selected_index,
            flags=sublime.QuickPanelFlags.WANT_EVENT,
            on_select=lambda index, event=None: self.on_done(index, items, stack, initial_selection, event),
            on_highlight=lambda index: self.on_highlight(index, items, stack, initial_selection)
        )

    def replace_spaces_with_spaces(self, text):
        match = re.match(r'^(\s+)', text)
        if match:
            spaces = match.group(1)
            return re.sub(r'^\s+', ' ' * len(spaces), text)
        else:
            return text

    # Gets the visible lines surrounding the current line
    def get_visible_lines(self, view: sublime.View, visible_lines, view_selection):
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
                # line_string = self.replace_spaces_with_spaces(line_string)

                if line_string != "":
                    line_strings.append(line_string)

            if line_strings.__len__() > 0:
                return line_strings

        return [fallback_line_string or ""]

    def on_highlight(self, index, items, stack: ViewStack, selection):
        if index == -1:
            raise Exception("Cannot highlight index: -1")

        sheets = stack.get(index)

        if sheets is None and (len(stack.all()) <= index < len(items)):
            print("xxx", items[index])
            self.window.open_file(items[index], sublime.TRANSIENT)
            print(self.window.active_view())

        if sheets is not None:
            # print("has sheet!", sheets)
            self.highlighted_index = index
            self.window.select_sheets(sheets)

        state = plugin_state()
        state["highlighted_index"] = index

        ContextKeeperShowCommand.ignore_highlight=False

    def on_done(self, index, items, stack: ViewStack, selection, event):
        if index == -1:
            index = self.highlighted_index

        sheets = stack.get(index)

        state = plugin_state()
        state["is_quick_panel_open"] = False

        if sheets is None and (len(stack.all()) <= index < len(items)):
            print("selected transient!", items[index])
            # self.window.open_file(items[index])
            return

        if sheets is None:
            print("Sheets is missing!")
            # raise Exception("Sheets is missing!")
            return

        if ContextKeeperShowCommand.ignore_highlight is True:
            return

        self.window.select_sheets(sheets)
