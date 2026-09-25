import os
import sublime

from ...sheet_group import SheetGroup
from ...utils import dict_deep_get, parse_sheet, plugin_settings, plugin_state
from ...view_stack import ViewStack
from ..plugin_base import CompassPlugin

ITEM_TYPE = "compass_plugin_mru_tabs"


def is_mru_rows_enabled() -> bool:
    """
    Temporary rollback switch (STR-27 Phase 1-3). Default off = legacy
    core rows in show.py. Dies in Phase 4 with the old path — never a
    user preference.
    """
    try:
        settings = plugin_settings()
        return dict_deep_get(settings, "flags.mru_plugin.enabled", False) is True
    except Exception:
        return False


def generate_alias_trigger(window: sublime.Window, file_label, tags):
    """
    Folder-stripped, tags-prefixed row label for the per-file alias rows
    (tags-only view of the same open tabs). Temporary duplicate of the
    alias logic in show.py — the core copy dies in Phase 4.
    """
    settings = plugin_settings()
    open_folders = window.folders()
    is_tags_enabled = settings.get("enable_tags")

    for folder in open_folders:
        file_label = file_label.replace("%s%s" % (folder, os.path.sep), "")

    if is_tags_enabled is True and len(tags) > 0:
        file_label = "%s%s%s" % (' '.join(tags), ' | ', file_label)

    return file_label


class CompassPluginMruTabs(CompassPlugin):
    def __init__(self):
        self._window = None

    def get_id(self):
        return ITEM_TYPE

    def get_plugin_tag(self):
        # MRU rows are core rows, not plugin rows — no tag appended.
        return ""

    def is_enabled(self):
        return is_mru_rows_enabled()

    def on_load(self):
        # No-op until Phase 2 (tracking delegation). Subscribes nothing.
        return None

    def on_unload(self):
        # STACK persists for the session; nothing to release.
        return None

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
        # separately and concatenate AFTER all mains — the legacy path
        # appends mains to items and aliases to post_list, joining them
        # as items + post_list. Interleaving per group is wrong.
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
