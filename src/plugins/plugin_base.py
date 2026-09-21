import sublime


class CompassPlugin:
    """
    Base interface for compass panel plugins.

    Subclass this and register an instance inside plugin_loaded() via
    plugins_registry.register_plugin(...). The Files plugin is the
    bundled reference implementation; `Compass Plugin - Markdown` is an
    external third-party example.

    Item contract: generate_items returns item details and
    Compass builds the QuickPanelItem, enforcing get_plugin_tag(). Plugins that
    still return QuickPanelItem lists keep working via the legacy path in
    CompassShowCommand, but new plugins must use details-only.
    """

    def get_id(self) -> str:
        """
        Stable internal routing key. Used as kind[2] and matched by
        is_applicable. Not user-facing (see get_plugin_tag).
        """
        raise NotImplementedError

    def get_plugin_tag(self) -> str:
        """
        Tag Compass appends to every item trigger (e.g. "#open").
        Always applied, regardless of the enable_tags setting.
        """
        return ""

    def is_enabled(self) -> bool:
        """
        Check settings. Return False to skip this plugin entirely.
        """
        return True

    def on_load(self) -> None:
        """
        Called once by load_plugins() when Compass loads. Subscribe to
        events or kick off background work here. No-op by default.
        """
        return None

    def on_unload(self) -> None:
        """
        Called when Compass unloads. Release whatever on_load set up.
        No-op by default.
        """
        return None

    def refresh_cache(self, window: sublime.Window) -> None:
        """
        Rebuild the plugin's internal data. Called before generate_items.
        """
        return None

    def generate_items(self, project_id: str):
        """
        Return (details, meta) for the given project.

        details is a list of dicts with the QuickPanelItem fields the
        plugin owns: {"trigger": str, "details": str, "annotation": str,
        "kind": (KindId, shortcut)}. Only "trigger" is required; the
        rest default to "" and (COLOR_YELLOWISH, "p"). Compass builds
        the QuickPanelItem, appends get_plugin_tag() to the trigger,
        and sets kind[2] to the plugin id and kind[3] to the meta
        object. meta is a parallel list of plugin-specific objects.
        (Legacy: returning a list of QuickPanelItem still works, but
        new plugins must use details dicts.)
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
