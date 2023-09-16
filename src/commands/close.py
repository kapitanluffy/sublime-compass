import sublime_plugin

class CompassCloseCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()

        if view is None:
            return

        sheet = view.sheet()

        if sheet is None:
            return

        # @note experimenting on including unopened files
        # file_name = view.file_name()

        # if sheet.is_transient():
            # self.window.promote_sheet(sheet)
            # view = self.window.open_file(file_name)
            # self.window.focus_view(view)
            # print("z", view, view.sheet(), sheet, sheet.is_transient(), view.is_valid())
            # self.focus_transient_sheet(sheet, view)
            # sublime.set_timeout_async(lambda s=sheet, v=view: self.focus_transient_sheet(sheet, view), 100)

        self.window.run_command("hide_overlay")

    # def focus_transient_sheet(self, sheet, view):
        # self.window.promote_sheet(sheet)
        # self.window.select_sheets([sheet])
        # self.window.focus_view(view)
        # print("zz", view, view.sheet(), sheet)
