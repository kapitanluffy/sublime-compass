import sublime
import sublime_plugin
from ..utils import *
from .stack import STACK, append_sheets, cache_stack, hydrate_stack, remove_window
from .view_stack import ViewStack


# Build the stack from window object
def build_stack(window: sublime.Window):
    sheets = window.sheets()
    groups = window.num_groups()

    for group in range(groups):
        sheets = window.sheets_in_group(group)
        for sheet in sheets:
            append_sheets(window, [sheet], group)


def is_view_valid_tab(view):
    return view.element() is not None and view.element() != "find_in_files:output"


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
        is_hydrated = hydrate_stack(window)

        if is_hydrated is False:
            build_stack(window)

    def on_pre_close_window(self, window: sublime.Window):
        remove_window(window)

    def on_pre_close_project(self, window: sublime.Window):
        remove_window(window)

    def on_pre_close(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is not None and sheet.is_transient():
            return

        if is_view_valid_tab(view):
            return

        window = view.window()
        sheet = view.sheet()

        if window is None:
            # plugin_debug("Window for View #%s is gone" % view.id())
            return

        if sheet is None:
            plugin_debug("Sheet for View #%s is gone" % view.id())
            return

        group = sheet.group() or window.active_group()
        stack = ViewStack(window, group)
        stack.remove(sheet)

        state = plugin_state()
        if state["is_quick_panel_open"] is True:
            window.run_command("compass_close", {"reset": True})

    def on_activated_async(self, view: sublime.View):
        sheet = view.sheet()

        if sheet is None:
            return

        if sheet is not None and sheet.is_transient():
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
        cache_stack(window)
