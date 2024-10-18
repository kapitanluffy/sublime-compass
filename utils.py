import sublime

PLUGIN_STATE = {
    "is_quick_panel_open": False,
    "highlighted_index": 0,
    "is_reset": True,
}


def plugin_state():
    return PLUGIN_STATE


def reset_plugin_state():
    state = plugin_state()
    state["is_quick_panel_open"] = False
    state["highlighted_index"] = 0
    state["is_reset"] = True


def plugin_debug(*message):
    settings = sublime.load_settings("Compass Navigator.sublime-settings")

    if settings["debug"] is True:
        print(*message)


def plugin_settings():
    return sublime.load_settings("Compass Navigator.sublime-settings")
