from typing import List, Union
import sublime
import sublime_plugin
from ...utils import plugin_debug, plugin_settings, plugin_state
from ..file import File
from ..view_stack import ViewStack
from ..sheet_group import SheetGroup
from ..plugins.files import CompassPluginFileStack
from ..stack import STACK, cache_stack
from ..utils import parse_sheet, dict_deep_get
import os


def generate_post_file_item(window: sublime.Window, file_label, tags, kind, annotation):
    settings = plugin_settings()
    open_folders = window.folders()
    is_tags_enabled = settings.get("enable_tags")

    for folder in open_folders:
        file_label = file_label.replace("%s%s" % (folder, os.path.sep), "")

    if is_tags_enabled is True and len(tags) > 0:
        file_label = "%s%s%s" % (' '.join(tags), ' | ', file_label)

    return sublime.QuickPanelItem(trigger=file_label, kind=kind, annotation=annotation)


def _sheet_name(sid: int) -> str:
    sheet = sublime.Sheet(sid)
    view = sheet.view()
    if view is None:
        return "DEAD:%d" % sid
    fname = view.file_name()
    if fname:
        return fname
    vname = view.name()
    if vname:
        return vname
    return "NOFILE:%d" % sid


class CompassShowCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        settings = plugin_settings()
        state = plugin_state()

        is_forward = kwargs.get('forward', True)

        group = self.window.active_group()

        if settings.get('only_show_items_in_focused_group', True) is False:
            group = None

        stack = ViewStack(self.window, group)

        # @note show quick panel even if window is empty

        items: List[sublime.QuickPanelItem] = []
        # @note showing quickpanel does not need a current_view

        initial_selection = self.window.selected_sheets_in_group(self.window.active_group())
        state["initial_selection_ids"] = [s.id() for s in initial_selection]
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
            valid_sheets = []

            for sheet in sheets:
                parsedSheet = parse_sheet(sheet)

                if parsedSheet is False:
                    continue

                names.append(parsedSheet['name'])
                files.append(parsedSheet['file'])
                tags = tags.union(parsedSheet['tags'])
                valid_sheets.append(sheet)

                if preview == "":
                    preview = parsedSheet['preview']

                if kind is None:
                    kind = parsedSheet['kind']

            if names.__len__() <= 0:
                continue

            # Update the sheets in the stack with only valid sheets
            if len(valid_sheets) > 0 and len(valid_sheets) != len(sheets):
                sheets[:] = valid_sheets

            trigger = ' + '.join(names)
            is_tags_enabled = settings.get('enable_tags', False)
            annotation = ' '.join(tags) if is_tags_enabled else ''
            item = sublime.QuickPanelItem(trigger=trigger, kind=kind, details=preview, annotation=annotation)
            items.append(item)
            items_meta.append(sheets)

            if is_tags_enabled:
                for index, file in enumerate(files):
                    item = generate_post_file_item(self.window, file or names[index], tags, kind, trigger)
                    post_list.append(item)
                    post_list_meta.append(sheets)

        file_types_items: List[sublime.QuickPanelItem] = []
        file_types_meta = []

        only_show_unopened_files_on_empty_window = settings.get("only_show_unopened_files_on_empty_window", True)
        plugin_files_enable_cache = dict_deep_get(settings, "plugins.files.enable_cache")
        plugin_files_enabled = dict_deep_get(settings, "plugins.files.enabled")

        # @todo might need to move this chunk inside generate_items?
        if plugin_files_enabled is True and plugin_files_enable_cache is False and \
           only_show_unopened_files_on_empty_window is False or \
           (only_show_unopened_files_on_empty_window is True and len(self.window.sheets()) <= 0):
            CompassPluginFileStack.refresh_cache(self.window)

        # @todo need to make this identifier more portable
        projectId = self.window.project_file_name() or str(self.window.id())
        unopened_files_items, unopened_files_meta = CompassPluginFileStack.generate_items(projectId) if plugin_files_enabled is True else ([], [])

        items = items + post_list + unopened_files_items + file_types_items

        # Right now, the items_meta is just for checking sheet_groups
        # We are slowly moving away from sheet_groups
        items_meta = items_meta + post_list_meta + unopened_files_meta + file_types_meta

        if len(items) <= 0 or len(items_meta) <= 0:
            return

        state["is_quick_panel_open"] = True
        state["highlighted_index"] = selected_index

        self.window.show_quick_panel(
            items=items,
            selected_index=selected_index,
            on_select=lambda index: self.on_done(index, items, items_meta),
            on_highlight=lambda index: self.on_highlight(index, items, initial_selection, items_meta)
        )

    def on_highlight(self, index: int, items, initial_selection, items_meta: List[Union[SheetGroup, File]]):
        if index == -1:
            raise Exception("Cannot highlight index: -1")

        selected_item = items[index]
        settings = plugin_settings()
        sheets = items_meta[index]
        state = plugin_state()
        state["highlighted_index"] = index

        is_preview_on_highlight = settings.get("preview_on_highlight", True)

        if is_preview_on_highlight is False:
            return

        if CompassPluginFileStack.is_applicable(selected_item):
            CompassPluginFileStack.on_highlight(selected_item, self.window)
            return

        if isinstance(sheets, SheetGroup) and sheets is not None:
            # Select sheets (for preview) only when head's group is the active group
            # use the inital selection if not
            if len(sheets) > 0 and sheets[0].group() == self.window.active_group():
                self.window.select_sheets(sheets)
            else:
                self.window.select_sheets(initial_selection)

    def on_done(self, index, items, items_meta: List[Union[SheetGroup, File]]):
        state = plugin_state()
        state["is_quick_panel_open"] = False
        cache_stack(self.window, force=True)

        try:
            if 0 <= index < len(items):
                selected_item = items[index]
                meta = items_meta[index]

                if isinstance(meta, SheetGroup) and len(meta) > 0:
                    window_sheet_ids = [s.id() for s in self.window.sheets()]
                    row_ids = [s.id() for s in meta]
                    focused = meta.get_focused()
                    stack_ids = [block for block in STACK if block[0] == self.window.id()]
                    print("COMPASS_HUNT on_done sheet_group", {
                        "index": index,
                        "trigger": selected_item.trigger,
                        "row_sheet_ids": ["%s(%d)" % (_sheet_name(s), s) for s in row_ids],
                        "row_transient": [s.is_transient() for s in meta],
                        "focused_id": focused.id() if focused is not None else None,
                        "focused_name": _sheet_name(focused.id()) if focused is not None else None,
                        "focused_in_window": focused is not None and focused.id() in window_sheet_ids,
                        "focused_in_row": focused is not None and focused.id() in row_ids,
                        "active_group": self.window.active_group(),
                        "meta_group": meta[0].group(),
                        "initial_selection_ids": state.get("initial_selection_ids", []),
                        "stack_blocks": [{"group": b[1], "ids": [_sheet_name(i) for i in b[2]], "focused": _sheet_name(b[3])} for b in stack_ids],
                        "window_sheet_ids": len(window_sheet_ids),
                    })
                elif isinstance(meta, File):
                    print("COMPASS_HUNT on_done file", {
                        "index": index,
                        "trigger": selected_item.trigger,
                        "full_path": meta.get_full_path(),
                    })
        except Exception as e:
            print("COMPASS_HUNT error", e)

        if index == -1 and state["is_reset"] is True:
            index = 0

        if index == -1 and state["is_reset"] is False:
            index = state["highlighted_index"]
            state["is_reset"] = True

        sheets = items_meta[index]
        selected_item = items[index]
        if CompassPluginFileStack.is_applicable(selected_item):
            state["is_quick_panel_open"] = False
            CompassPluginFileStack.on_select(selected_item, self.window)
            sublime.set_timeout(lambda item=selected_item: print("COMPASS_HUNT after_file_open", {
                "target": item.kind[3][0],
                "active_file": self.window.active_view().file_name() if self.window.active_view() is not None else None,
                "active_sheet_id": self.window.active_sheet().id() if self.window.active_sheet() is not None else None,
            }), 0)
            return

        # @todo on plugin reload, sheets are still SheetGroup because it is a subclass of List.
        if isinstance(sheets, SheetGroup) and sheets is not None:
            state["is_quick_panel_open"] = False
            self.window.select_sheets(sheets)

            # refocus on the selected sheet
            focused = sheets.get_focused()
            sheet_ids = [s.id() for s in sheets]
            if focused is None or focused.id() not in sheet_ids:
                focused = sheets[0] if len(sheets) > 0 else None
            if len(sheets) > 0 and focused is not None:
                self.window.focus_sheet(focused)
                sublime.set_timeout(lambda f=focused: print("COMPASS_HUNT after_focus_sheet", {
                    "target_focused_id": f.id(),
                    "target_focused_name": _sheet_name(f.id()),
                    "active_file": self.window.active_view().file_name() if self.window.active_view() is not None else None,
                    "active_sheet_id": self.window.active_sheet().id() if self.window.active_sheet() is not None else None,
                }), 0)
            return
