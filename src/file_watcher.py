import sublime
import sublime_plugin
# from FileWatcher.src.file_event_listener import FileEventListener


class CompassFileEventListener(sublime_plugin.EventListener):
    def on_window_command(self, window: sublime.Window, command_name: str, args):
        if command_name != "file_watcher_broadcast_event":
            return

        events = args['_events']

        for event, files in events:

            if event == "create":
                self.on_create(files, window)

            if event == "change":
                self.on_change(files, window)

            if event == "delete":
                self.on_delete(files, window)

        pass

    def on_create(self, files, window):
        print("create!", files, window)
        pass

    def on_change(self, files, window):
        print("change!", files, window)
        pass

    def on_delete(self, files, window):
        print("delete!", files, window)
        pass
