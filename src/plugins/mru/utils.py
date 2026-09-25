"""MRU tabs plugin utilities - Compass Navigator bundled plugin.

Pure policy helpers: the alias-label builder plus the max-open-tabs
cleanup. State writes (STACK) stay in plugin.py with the class — this
module never imports it, so the dependency runs one way
(plugin -> utils, no cycle).
"""

import os
import sublime

from ...utils import plugin_settings
from ...view_stack import ViewStack


def generate_alias_trigger(window: sublime.Window, file_label, tags):
    # Folder-stripped, tags-prefixed alias label. Moved from show.py —
    # the core copy is gone, this is the only one.
    settings = plugin_settings()
    open_folders = window.folders()
    is_tags_enabled = settings.get("enable_tags")

    for folder in open_folders:
        file_label = file_label.replace("%s%s" % (folder, os.path.sep), "")

    if is_tags_enabled is True and len(tags) > 0:
        file_label = "%s%s%s" % (' '.join(tags), ' | ', file_label)

    return file_label


def cleanup_sheets(stack: ViewStack):
    # MRU policy: discard the least-recent open tab when max_open_tabs
    # is met. Moved verbatim from src/events.py.
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
