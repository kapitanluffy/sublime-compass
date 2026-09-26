from typing import List, Tuple, Union
import sublime
import sublime_plugin
import time
from ...utils import plugin_debug, plugin_settings, plugin_state
from ..view_stack import ViewStack
from ..sheet_group import SheetGroup
from ..plugins_registry import dispatch_event, get_plugins
from ..stack import cache_stack


def _is_claimed(item) -> bool:
    # Mirrors dispatch: True when an enabled plugin owns this row.
    for plugin in get_plugins():
        try:
            if plugin.is_enabled() is False:
                continue
            if plugin.is_applicable(item):
                return True
        except Exception:
            continue
    return False


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

        # @note show quickpanel does not need a current_view

        initial_selection = self.window.selected_sheets_in_group(self.window.active_group())
        state["initial_selection_ids"] = [s.id() for s in initial_selection]
        stack_length = len(stack.all())
        selected_index = 0

        if settings["jump_to_most_recent_on_show"] is True:
            selected_index = 1

        if is_forward is False:
            selected_index = stack_length - 1

        # Tab rows (mains + aliases) arrive via the MRU plugin dispatch
        # loop below; unopened-file rows via the Files plugin.
        # @todo need to make this identifier more portable
        projectId = self.window.project_file_name() or str(self.window.id())

        plugin_items: List[sublime.QuickPanelItem] = []
        plugin_meta: List = []
        build_started = time.perf_counter()
        for plugin in get_plugins():
            if not plugin.is_enabled():
                continue
            try:
                plugin.refresh_cache(self.window)
                p_result, p_meta = plugin.generate_items(projectId)
                if len(p_result) > 0 and isinstance(p_result[0], sublime.QuickPanelItem):
                    # Legacy path: plugin built its own items.
                    plugin_items.extend(p_result)
                    plugin_meta.extend(p_meta)
                else:
                    # Details path: Compass builds the items and always
                    # appends the plugin tag to the trigger.
                    tag = getattr(plugin, "get_plugin_tag", lambda: "")() or ""
                    for detail, m in zip(p_result, p_meta):
                        trigger = detail["trigger"]
                        if tag:
                            trigger = "%s %s" % (tag, trigger)
                        kind_base = detail.get(
                            "kind", (sublime.KindId.COLOR_YELLOWISH, "p")
                        )
                        kind = (kind_base[0], kind_base[1], plugin.get_id(), m)
                        plugin_items.append(
                            sublime.QuickPanelItem(
                                trigger=trigger,
                                details=detail.get("details", ""),
                                annotation=detail.get("annotation", ""),
                                kind=kind,
                            )
                        )
                        plugin_meta.append(m)
            except Exception as e:
                print("Compass plugin error in %s: %s" % (plugin.get_id(), e))

        items = plugin_items

        build_ms = int((time.perf_counter() - build_started) * 1000)
        plugin_debug("Compass panel build: %d rows in %dms" % (len(items), build_ms))

        # items_meta holds SheetGroups (open tabs) + plugin payloads;
        # plugins claim their rows via is_applicable first, the SheetGroup
        # check below is the fallback for open tabs (needs live Sheets, STR-16).
        items_meta = plugin_meta

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

    def on_highlight(self, index: int, items, initial_selection, items_meta: List[Union[SheetGroup, Tuple[str, str, str]]]):
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

        dispatch_event(self.window, "highlight",
            item=selected_item, meta=items_meta[index])

        if _is_claimed(selected_item):
            return

        if isinstance(sheets, SheetGroup) and sheets is not None:
            # Select sheets (for preview) only when head's group is the active group
            # use the inital selection if not
            if len(sheets) > 0 and sheets[0].group() == self.window.active_group():
                self.window.select_sheets(sheets)
            else:
                self.window.select_sheets(initial_selection)

    def on_done(self, index, items, items_meta: List[Union[SheetGroup, Tuple[str, str, str]]]):
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
        dispatch_event(self.window, "select",
            item=selected_item, meta=items_meta[index])
        if _is_claimed(selected_item):
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
