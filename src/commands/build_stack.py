import sublime
import sublime_plugin
from ..stack_manager import StackManager
from ...utils import plugin_settings, plugin_debug

class CompassBuildStackCommand(sublime_plugin.WindowCommand):
    is_building = False

    def is_enabled(self):
        return CompassBuildStackCommand.is_building != True

    def run(self):
        CompassBuildStackCommand.is_building = True
        group = self.window.active_group()
        stack = StackManager.get(self.window, group)
        stack.clear()
        view_count = self.window.num_views_in_group(group)
        delay_multiplier = 1
        delay_base = 5

        print("build mru stack >>")
        for i in range(view_count):
            sublime.set_timeout(lambda t=view_count: self.build_stack(t), delay_base * delay_multiplier)
            delay_multiplier = delay_multiplier + i

        sublime.set_timeout_async(lambda: self.build_done(), (delay_base * 2) * (view_count + 1))

    def build_stack(self, view_count):
        settings = plugin_settings()
        group = self.window.active_group()
        stack = StackManager.get(self.window, group)
        # self.window.active_view().set_status("compass_status", "Building MRU stack..")

        if stack.sheet_total() == view_count:
            return

        sheets = self.window.selected_sheets()
        stack.append(self.window, sheets, group)

        if settings["debug"] is True:
            self._dump_stack(sheets)

        self.window.run_command("next_view_in_stack")

    def build_done(self):
        # self.window.active_view().erase_status("compass_status")
        CompassBuildStackCommand.is_building = False

    def _dump_stack(self, sheets):
        _sheet_names = []
        for _sheet in sheets:
            view = _sheet.view()
            name = _sheet.file_name()
            _sheet_names.append(
                view.name() if view is not None and name is None else name
            )

        plugin_debug("\t%s" % _sheet_names)
