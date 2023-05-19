import sublime
import sublime_plugin
from .utils import plugin_settings, plugin_state
from .view_stack import ViewStack
from .stack_manager import StackManager
import copy
import os
from typing import List

class RecentlyUsedExtendedShowCommand(sublime_plugin.WindowCommand):
    ignore_highlight = False

    def run(self, **kwargs):
        settings = plugin_settings()
        RecentlyUsedExtendedShowCommand.ignore_highlight = False
        self.highlighted_index = -1
        is_forward = kwargs.get('forward', True)

        group = self.window.active_group()
        stack = StackManager.get(self.window, group)

        if self.window.views_in_group(0).__len__() <= 0:
            return

        if stack.sheet_total() == 0:
            print("new stack! building stack! #2")
            self.window.run_command("recently_used_extended_build_stack")

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

            for sheet in sheets:
                view = sheet.view()
                file_name = sheet.file_name()

                if file_name:
                    name = os.path.basename(file_name)
                elif view is not None:
                    name = view.name()
                else:
                    name = "Untitled #%s" % sheet.id()

                names.append(name)

            trigger = ', '.join(names)
            item = sublime.QuickPanelItem(trigger=trigger, annotation=annotation, kind=sublime.KIND_FUNCTION)
            items.append(item)

        # folders = self.window.folders()
        # for folder in folders:
        #     for root, dirs, files in os.walk(folder):
        #         for file in files:
        #             items.append(os.path.join(root, file))

        state = plugin_state()
        state["is_quick_panel_open"] = True

        self.window.show_quick_panel(
            items=items,
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
            print("xxx", items[index])
            self.window.open_file(items[index], sublime.TRANSIENT)
            print(self.window.active_view())

        if sheets is not None:
            # print("has sheet!", sheets)
            self.highlighted_index = index
            self.window.select_sheets(sheets)

        RecentlyUsedExtendedShowCommand.ignore_highlight=False

    def on_done(self, index, items, stack: ViewStack, selection, event):
        if index == -1:
            index = self.highlighted_index

        sheets = stack.get(index)

        if sheets is None and (len(stack.all()) <= index < len(items)):
            print("selected transient!", items[index])
            # self.window.open_file(items[index])
            return

        if sheets is None:
            print("Sheets is missing!")
            # raise Exception("Sheets is missing!")
            return

        if RecentlyUsedExtendedShowCommand.ignore_highlight is True:
            return

        state = plugin_state()
        state["is_quick_panel_open"] = False
        self.window.select_sheets(sheets)
