"""MRU tabs - Compass Navigator bundled plugin."""

import sublime

from ...sheet_group import SheetGroup
from ...stack import cache_stack, hydrate_stack, remove_window
from ...utils import parse_sheet, plugin_settings, plugin_state
from ...view_stack import ViewStack
from ..plugin_base import CompassPlugin
from .utils import cleanup_sheets, generate_alias_trigger

ITEM_TYPE = "compass_plugin_mru_tabs"


class CompassPluginMruTabs(CompassPlugin):
    def __init__(self):
        self._window = None

    def get_id(self):
        return ITEM_TYPE

    def get_plugin_tag(self):
        # MRU rows are core rows, not plugin rows — no tag appended.
        return ""

    def is_enabled(self):
        # Bundled plugin: always on. Third-party gating
        # (flags.plugin_support) does not apply to bundled ids.
        return True

    def on_load(self):
        # Import-time registration (see __init__) leaves nothing to set
        # up. This print doubles as the load proof in the console.
        print("CompassNavigator - MRU tabs plugin - loaded!")
        return None

    def on_unload(self):
        # STACK persists for the session; nothing to release.
        return None

    def on_sheet_activated(self, window: sublime.Window, sheet: sublime.Sheet, group: int):
        # MRU write on tab switch. Core vets the event, dispatches here.
        stack = ViewStack(window, group)
        sheets = window.selected_sheets_in_group(group)
        stack.push(window, sheets, group, sheet)
        cleanup_sheets(stack)
        cache_stack(window)

    def on_sheet_closed(self, window: sublime.Window, sheet: sublime.Sheet):
        # MRU forget on tab close.
        group = sheet.group() or window.active_group()
        ViewStack(window, group).remove(sheet)

    def on_window_closed(self, window: sublime.Window):
        remove_window(window)

    def on_project_closed(self, window: sublime.Window):
        remove_window(window)

    def on_project_loaded(self, window: sublime.Window):
        hydrate_stack(window)

    def refresh_cache(self, window: sublime.Window):
        # The protocol hands us the window here; generate_items only gets
        # a project id. Stashed for the generate_items call right after,
        # in the same dispatch-loop iteration (show.py).
        self._window = window
        return None

    def generate_items(self, projectId):
        window = self._window
        if window is None:
            return ([], [])

        settings = plugin_settings()
        group = window.active_group()
        if settings.get('only_show_items_in_focused_group', True) is False:
            group = None

        details = []
        meta = []
        # Alias rows (tags-only view of the same tabs) accumulate
        # separately and concatenate AFTER all mains. Interleaving
        # per group is wrong.
        alias_details = []
        alias_meta = []

        for sheets in ViewStack(window, group).all():
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

            # Boundary note: sheets backs core's STACK items — this prune
            # writes into core-owned objects (same as the legacy path did).
            # Storage itself stays in core (STR-27 choice 2: adapter).
            if len(valid_sheets) > 0 and len(valid_sheets) != len(sheets):
                sheets[:] = valid_sheets

            is_tags_enabled = settings.get('enable_tags', False)
            annotation = ' '.join(tags) if is_tags_enabled else ''
            details.append({
                "trigger": ' + '.join(names),
                "details": preview,
                "annotation": annotation,
                "kind": kind,
            })
            meta.append(sheets)

            if is_tags_enabled:
                trigger = ' + '.join(names)
                for index, file in enumerate(files):
                    alias = generate_alias_trigger(window, file or names[index], tags)
                    alias_details.append({
                        "trigger": alias,
                        "details": "",
                        "annotation": trigger,
                        "kind": kind,
                    })
                    alias_meta.append(sheets)

        return (details + alias_details, meta + alias_meta)

    def is_applicable(self, item: sublime.QuickPanelItem):
        return item.kind[2] == ITEM_TYPE

    def on_highlight(self, item: sublime.QuickPanelItem, meta, window: sublime.Window):
        # Moved from the SheetGroup fallback in show.on_highlight (STR-27
        # choice 3: plugin acts, core signals). The preview_on_highlight
        # gate stays in core and runs before dispatch.
        sheets = meta
        if isinstance(sheets, SheetGroup) and sheets is not None:
            # Select sheets (for preview) only when head's group is the active group
            # use the inital selection if not
            if len(sheets) > 0 and sheets[0].group() == window.active_group():
                window.select_sheets(sheets)
            else:
                initial_ids = plugin_state().get("initial_selection_ids", [])
                window.select_sheets([sublime.Sheet(sid) for sid in initial_ids])

    def on_select(self, item: sublime.QuickPanelItem, meta, window: sublime.Window):
        # Moved from the SheetGroup fallback in show.on_done. Panel state
        # (close, Esc-cancel) and the forced cache write stay in core.
        sheets = meta
        if isinstance(sheets, SheetGroup) and sheets is not None:
            window.select_sheets(sheets)

            # refocus on the selected sheet
            focused = sheets.get_focused()
            sheet_ids = [s.id() for s in sheets]
            if focused is None or focused.id() not in sheet_ids:
                focused = sheets[0] if len(sheets) > 0 else None
            if len(sheets) > 0 and focused is not None:
                window.focus_sheet(focused)


_PLUGIN_INSTANCE = CompassPluginMruTabs()
