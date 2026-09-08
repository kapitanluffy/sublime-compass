from typing import List, Union
import sublime
import sublime_plugin
from ...utils import plugin_settings, plugin_state
from ..view_stack import ViewStack
from ..sheet_group import SheetGroup
from ..plugins_registry import get_plugins
from ..plugins.files.file import File
from ..stack import cache_stack
from ..utils import parse_sheet
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

        # @todo need to make this identifier more portable
        projectId = self.window.project_file_name() or str(self.window.id())

        plugin_items: List[sublime.QuickPanelItem] = []
        plugin_meta: List = []
        for plugin in get_plugins():
            if not plugin.is_enabled():
                continue
            try:
                plugin.refresh_cache(self.window)
                p_items, p_meta = plugin.generate_items(projectId)
                plugin_items.extend(p_items)
                plugin_meta.extend(p_meta)
            except Exception as e:
                print("Compass plugin error in %s: %s" % (plugin.get_id(), e))

        items = items + post_list + plugin_items + file_types_items

        # Right now, the items_meta is just for checking sheet_groups
        # We are slowly moving away from sheet_groups
        items_meta = items_meta + post_list_meta + plugin_meta + file_types_meta

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

        for plugin in get_plugins():
            if plugin.is_applicable(selected_item):
                meta = items_meta[index]
                plugin.on_highlight(selected_item, meta, self.window)
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

        if index == -1 and state["is_reset"] is True:
            index = 0

        if index == -1 and state["is_reset"] is False:
            index = state["highlighted_index"]
            state["is_reset"] = True

        sheets = items_meta[index]
        selected_item = items[index]
        for plugin in get_plugins():
            if plugin.is_applicable(selected_item):
                state["is_quick_panel_open"] = False
                meta = items_meta[index]
                plugin.on_select(selected_item, meta, self.window)
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
            return
