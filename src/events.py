import sublime
import sublime_plugin
from ..utils import *
from .stack import cache_stack, hydrate_stack, remove_window
from .view_stack import ViewStack


def is_view_valid_tab(view):
    return view.element() is not None and view.element() != "find_in_files:output"


# Discard the most unused item if max_open_tabs is met
def cleanup_sheets(stack: ViewStack):
    settings = plugin_settings()
    max_open_tabs = settings.get('max_open_tabs', 100)  # type: int

    if max_open_tabs == 0 or stack.length() <= max_open_tabs:
        return True

    stack_length = stack.length()

    for si in range(stack_length):
        index = stack_length - (si + 1)
        last_sheet_group = stack.all()[index]

        for s in last_sheet_group:
            sview = s.view()

            if sview is None:
                continue

            if sview.is_dirty() or sview.is_scratch():
                continue

            print("cleaning up", sview.file_name() or sview.name())

            s.close()
            return True


class CompassFocusListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key == "compass" and operator == 0 and operand is True:
            return True
        return False

    def on_load_project_async(self, window):
        hydrate_stack(window)

    def on_pre_close_window(self, window: sublime.Window):
        remove_window(window)

    def on_pre_close_project(self, window: sublime.Window):
        remove_window(window)

    def on_pre_close(self, view: sublime.View):
        state = plugin_state()
        sheet = view.sheet()

        if sheet is None:
            return

        if is_view_valid_tab(view):
            return

        window = view.window()

        if window is None:
            # plugin_debug("Window for View #%s is gone" % view.id())
            return

        if sheet.is_transient():
            if state["is_quick_panel_open"] is True:
                window.run_command("compass_close", {"reset": True})
            return

        group = sheet.group() or window.active_group()
        stack = ViewStack(window, group)
        stack.remove(sheet)

        if state["is_quick_panel_open"] is True:
            window.run_command("compass_close", {"reset": True})

    def on_activated_async(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is None or sheet.is_transient():
            return

        if is_view_valid_tab(view):
            return

        window = view.window()

        if window is None:
            # plugin_debug("Window for View #%s is a None xxx" % view.id())
            return

        if window.views().__len__() <= 0:
            return

        group = sheet.group() or window.active_group()
        stack = ViewStack(window, group)
        sheets = window.selected_sheets_in_group(group)
        stack.push(window, sheets, group, sheet)
        cleanup_sheets(stack)

        # Save the stack cache on every view change
        cache_stack(window)
