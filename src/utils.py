import sublime
import os
import re
import subprocess
from typing import List
from ..utils import plugin_settings
from . import File

KIND_VIEW = (sublime.KindId.COLOR_REDISH, "f", "File")
KIND_VIEW_SCRATCH = (sublime.KindId.COLOR_GREENISH, "s", "Scratch")
KIND_VIEW_DIRTY = (sublime.KindId.COLOR_CYANISH, "d", "Dirty")
KIND_VIEW_FINDFILES = (sublime.KindId.COLOR_BLUISH, "?", "FindFiles")
KIND_VIEW_PRIMARY = (sublime.KindId.COLOR_PINKISH, "P", "PrimaryView")
KIND_VIEW_CLONE = (sublime.KindId.COLOR_PINKISH, "c", "CloneView")
KIND_FILE_TYPE = (sublime.KindId.COLOR_BLUISH, "t", "FileType")


def list_files(directory="."):
    settings = plugin_settings()
    ripgrep = str(settings.get("ripgrep_path", ""))

    if ripgrep == "" or os.path.exists(ripgrep) is False:
        return None

    command = [settings["ripgrep_path"], "--files", directory]

    try:
        # Run the command and capture the output
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,  # This makes sure the output is treated as text (str) rather than bytes
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        if result.returncode != 0:
            print(result.stderr)

        return result.stdout.splitlines()
    except Exception as e:
        print(f"An error occurred: {e}")


def parse_listed_files(window: sublime.Window):
    folders = window.folders()
    items: List[File] = []

    for folder in folders:
        files = list_files(folder)

        if files is None:
            return None

        for file in files:
            items.append(File(file, folder))

        return items


def generate_view_meta(view: sublime.View):
    tags = set()
    kind = KIND_VIEW

    # Set item type
    # Normal sheet
    if view.file_name() is not None and view.element() is None:
        tags.add("#tabs")

    # Scratch sheet
    if view.file_name() is None and view.element() is None:
        tags.add("#scratch")
        kind = KIND_VIEW_SCRATCH

    # Dirty sheets
    if view.file_name() is not None and view.is_dirty():
        tags.discard('#tabs')
        tags.add("#dirty")
        kind = KIND_VIEW_DIRTY

    # Find results
    if view.element() == "find_in_files:output":
        tags.add("#search")
        kind = KIND_VIEW_FINDFILES

    # Sheets with clones
    if view.is_primary() is True and view.clones().__len__() > 0:
        tags.add("#primary")
        kind = KIND_VIEW_PRIMARY

    # Sheet clones
    if view.is_primary() is False and view.clones().__len__() > 0:
        tags.add("#clones")
        kind = KIND_VIEW_CLONE

    return {"kind": kind, "tags": tags}


def guess_sheet_name(sheet: sublime.Sheet):
    name = "Untitled #%s" % sheet.id()
    file_name = sheet.file_name()
    view = sheet.view()

    if file_name:
        name = os.path.basename(file_name)
    elif view is not None and view.name() != "":
        name = view.name()

    return name


def replace_spaces_with_spaces(text):
    match = re.match(r'^(\s+)', text)
    if match:
        spaces = match.group(1)
        return re.sub(r'^\s+', ' ' * len(spaces), text)
    else:
        return text


# Gets the visible lines surrounding the current line
def get_visible_lines(view: sublime.View, visible_lines, view_selection):
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
            # line_string = replace_spaces_with_spaces(line_string)

            if line_string != "":
                line_strings.append(line_string)

        if line_strings.__len__() > 0:
            return line_strings

    return [fallback_line_string or ""]


def generate_preview(view: sublime.View):
    visible_lines = view.lines(view.visible_region())
    selection = view.sel()

    if len(selection) <= 0:
        return ""

    view_selection = view.line(view.sel()[0].a)
    preview = view.substr(view_selection).strip()

    if preview.__len__() <= 0:
        preview_lines = get_visible_lines(view, visible_lines, view_selection)
        preview = preview_lines[0].lstrip() if preview_lines.__len__() > 0 and preview_lines[0].lstrip() != "" else preview

    # @todo for groups, show the preview for the currently active in that group
    return """<tt style='color:red'>%s</tt>""" % sublime.html.escape(preview)


def parse_sheet(sheet: sublime.Sheet):
    view = sheet.view()

    if view is None or view.is_valid() is False:
        return False

    name = guess_sheet_name(sheet)
    preview = generate_preview(view)
    viewMeta = generate_view_meta(view)
    kind = viewMeta['kind']
    tags = viewMeta['tags']
    file = sheet.file_name()

    return {"name": name, "preview": preview, "kind": kind, "tags": tags, "file": file}
