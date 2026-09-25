import sublime_plugin


class CompassBroadcastEventCommand(sublime_plugin.WindowCommand):
    # No-op hook for packages outside Compass (command string is the
    # contract, see BROADCAST_COMMAND in plugins_registry). Core always
    # runs this alongside dispatch_event; outsiders snoop the JSON
    # payload via on_window_command with zero Compass imports.
    def run(self, _event=None, **kwargs):
        return None
