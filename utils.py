import sublime

PLUGIN_STATE = {
    "is_quick_panel_open": False
}

def plugin_state():
    return PLUGIN_STATE

def plugin_debug(*message):
    settings = sublime.load_settings("Recently Used Extended.sublime-settings")

    if settings["debug"] is True:
        print(*message)

def plugin_settings():
    return sublime.load_settings("Recently Used Extended.sublime-settings")
