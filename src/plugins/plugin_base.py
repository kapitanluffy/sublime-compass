import sublime


class CompassPlugin:
    """
    Base interface for compass panel plugins.

    Subclass this and register an instance via
    plugins_registry.register_plugin(...). The Files plugin is the
    bundled reference implementation; `Compass Plugin - Folders` is an
    external third-party example.
    """

    def get_id(self) -> str:
        """
        Stable internal routing key. Used as kind[2] and matched by
        is_applicable. Not user-facing (see tags in generate_items).
        """
        raise NotImplementedError

    def is_enabled(self) -> bool:
        """
        Check settings. Return False to skip this plugin entirely.
        """
        return True

    def refresh_cache(self, window: sublime.Window) -> None:
        """
        Rebuild the plugin's internal data. Called before generate_items.
        """
        return None

    def generate_items(self, project_id: str):
        """
        Return (quick_panel_items, meta) for the given project.

        meta is a list of plugin-specific objects parallel to
        quick_panel_items. Each item's kind[3] must carry the meta
        object for that item.
        """
        raise NotImplementedError

    def is_applicable(self, item: sublime.QuickPanelItem) -> bool:
        """
        Check if a quick_panel_item belongs to this plugin.
        """
        return item.kind[2] == self.get_id()

    def on_highlight(self, item: sublime.QuickPanelItem, meta, window: sublime.Window) -> None:
        """
        Called when the user highlights an item in the quick panel.
        meta is the plugin-specific object for this item.
        """
        return None

    def on_select(self, item: sublime.QuickPanelItem, meta, window: sublime.Window) -> None:
        """
        Called when the user selects an item. Open/focus the target.
        """
        raise NotImplementedError
