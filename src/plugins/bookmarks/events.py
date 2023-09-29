from .stack import Stack, BookmarkStackItem
import sublime
import sublime_plugin


class CompassBookmarksListener(sublime_plugin.EventListener):
    def on_modified_async(self, view: sublime.View):
        sheet = view.sheet()
        window = view.window()

        if sheet is None or window is None:
            return

        group = sheet.group() or window.active_group()

        if group is None:
            return

        bookmarks = view.get_regions('bookmarks')
        current_bookmarks = [sublime.Region(*key) for key in Stack.get_stack().keys()]

        for region in view.sel():
            line = view.line(region)
            for bookmark in current_bookmarks:
                stack_item = Stack.get_stack().get(bookmark.to_tuple())
                if bookmark not in bookmarks and stack_item is not None and sheet in stack_item[2]:
                    print("bookmark moved >", bookmark, Stack.get_stack().keys(), stack_item)
                    Stack.remove_bookmark(bookmark)
            for bookmark in bookmarks:
                if line.contains(bookmark.a) and bookmark not in current_bookmarks:
                    sheets = window.selected_sheets_in_group(group)
                    Stack.push(bookmark, BookmarkStackItem(window, sheets, group, sheet))
                    print("bookmark moved <", bookmark, Stack.get_stack().keys())
        pass

    def on_post_text_command(self, view: sublime.View, command, args):
        if command != "toggle_bookmark":
            return

        sheet = view.sheet()
        window = view.window()

        if sheet is None or window is None:
            return

        group = sheet.group() or window.active_group()

        if group is None:
            return

        selections = view.sel()
        bookmarks = view.get_regions('bookmarks')

        for selection in selections:
            if selection not in bookmarks:
                Stack.remove_bookmark(selection)
            if selection in bookmarks:
                sheets = window.selected_sheets_in_group(group)
                Stack.push(selection, BookmarkStackItem(window, sheets, group, sheet))

        print("bookmarks>", Stack.get_stack())
        pass
