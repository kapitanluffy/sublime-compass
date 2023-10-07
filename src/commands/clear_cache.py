import sublime_plugin


class CompassClearCacheCommand(sublime_plugin.WindowCommand):
    def run(self):
        print("Compass cache cleared!")
        self.window.settings().erase('compass_stack_cache')
