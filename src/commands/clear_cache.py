import sublime_plugin

class CompassClearCacheCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        print("Compass cache cleared!")
        self.window.settings().erase('compass_stack_cache')
