import os
import re

import sublime
import sublime_plugin

from ..plugins_registry import external_plugins_enabled


PLUGIN_PREFIX = "Compass Plugin - "
PYTHON_VERSION = "3.8"


def sanitize_short_name(name):
    cleaned = (name or "").strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9\-_]", "", cleaned)
    cleaned = cleaned.strip("-_")
    return cleaned


def to_plugin_id(short):
    slug = short.lower().replace("-", "_")
    slug = re.sub(r"[^a-z0-9_]", "", slug).strip("_")
    if not slug:
        return ""
    if slug[0].isdigit():
        slug = "p_" + slug
    return "compass_plugin_" + slug


def to_class_name(short):
    parts = re.split(r"[-_ ]+", short)
    parts = [p for p in parts if p]
    name = "".join(p[:1].upper() + p[1:] for p in parts)
    name = re.sub(r"[^A-Za-z0-9]", "", name)
    if not name:
        return "SamplePlugin"
    if name[0].isdigit():
        name = "Compass" + name
    return name + "Plugin"


def to_tag(short):
    tag = re.sub(r"[^a-z0-9]", "", short.lower())
    if not tag:
        return "#sample"
    return "#" + tag


PLUGIN_TEMPLATE = '''\
"""__DISPLAY__ - Compass Navigator plugin (lean sample).

Details contract: generate_items returns item details (trigger, details,
annotation, kind) + meta and Compass builds the QuickPanelItem, always
appending get_plugin_tag() to the trigger. Register inside
plugin_loaded() only; no Compass imports at top level so this package
loads with zero traceback when Compass is absent. Requires
`.python-version` with `3.8` (written by the scaffold) so Sublime runs
this package on the 3.8 plugin host. Outgrowing one file? Split helpers
into `utils.py` (pure functions, no plugin state) and keep the class +
`_PLUGIN_INSTANCE` in `plugin.py` — the same shape as the bundled
Files/MRU plugins.
"""

try:
    import sublime
except ImportError:
    sublime = None

import importlib

# Fallback base so the module imports without Compass.
CompassPlugin = object
COMPASS_AVAILABLE = False

PLUGIN_ID = "__PLUGIN_ID__"
SETTINGS_FILE = "__SETTINGS_FILE__"
TAG = "__TAG__"

# Lean static samples. Replace with your own source (ripgrep, LSP, git...).
_SAMPLES = ["foo", "bar", "baz"]
# MRU within this plugin: most recently selected first.
_RECENT = []


def _ordered_keys():
    return list(_RECENT) + [k for k in _SAMPLES if k not in _RECENT]


def _touch(key):
    if key in _RECENT:
        _RECENT.remove(key)
    _RECENT.insert(0, key)
    # Keep the list bounded to the sample set plus any touched keys.
    del _RECENT[len(_SAMPLES):]


def _log(msg):
    print("Compass Plugin - __DISPLAY__: %s" % (msg,))


class __CLASS_NAME__(CompassPlugin):
    def get_id(self):
        return PLUGIN_ID

    def get_plugin_tag(self):
        return TAG

    def is_enabled(self):
        if sublime is None:
            return True
        try:
            settings = sublime.load_settings(SETTINGS_FILE)
            return bool(settings.get("enabled", True))
        except Exception:
            return True

    def refresh_cache(self, window):
        # Lean sample: nothing to rebuild. Keep as the no-op hook.
        return None

    def generate_items(self, project_id):
        # Item details: trigger, details, annotation, kind. Compass
        # builds the QuickPanelItem and always prepends TAG to the trigger.
        if COMPASS_AVAILABLE is False:
            return ([], [])
        details = [
            {"trigger": key, "annotation": "__DISPLAY__"}
            for key in _ordered_keys()
        ]
        # Meta is your own object per row, handed back to you in
        # on_highlight/on_select. A dict keeps it self-describing;
        # the ordering key lives inside it.
        meta = [
            {"key": key, "source": "sample"}
            for key in _ordered_keys()
        ]
        return (details, meta)

    def is_applicable(self, item):
        try:
            return item.kind[2] == PLUGIN_ID
        except Exception:
            return False

    def on_highlight(self, window, item, meta):
        if not self.is_applicable(item):
            return
        _log("Highlighted: %s" % (meta,))

    def on_select(self, window, item, meta):
        if not self.is_applicable(item):
            return
        key = meta.get("key") if isinstance(meta, dict) else meta
        if key is not None:
            _touch(key)
        _log("Opened: %s" % (meta,))


_PLUGIN_INSTANCE = __CLASS_NAME__()


def plugin_loaded():
    global CompassPlugin, COMPASS_AVAILABLE
    # Broad guard: importing the registry executes the Compass parent
    # package chain, which can raise beyond ImportError on hosts where
    # Compass itself cannot load. Any failure silently disables.
    try:
        registry_mod = importlib.import_module(
            "Compass Navigator.src.plugins_registry"
        )
    except Exception:
        COMPASS_AVAILABLE = False
        return
    COMPASS_AVAILABLE = True
    try:
        registry_mod.register_plugin(_PLUGIN_INSTANCE)
    except Exception:
        return


def plugin_unloaded():
    global COMPASS_AVAILABLE
    COMPASS_AVAILABLE = False
'''

SETTINGS_TEMPLATE = '''\
{
// Set to false to hide this plugin's items in Compass.
"enabled": true
}
'''

README_TEMPLATE = '''\
# __DISPLAY__ (Compass Navigator plugin)

Lean sample plugin created by `Compass: Create Plugin`.

- `plugin.py` — static `foo / bar / baz` items with per-plugin MRU:
  select `baz` then `foo` and the panel lists `foo, baz, bar`.
  Details contract: `generate_items` returns item details + meta, Compass
  builds the `QuickPanelItem` and always prepends `TAG` (`__TAG__`) to
  every trigger.
- `<Short>.sublime-settings` — `"enabled": false` hides items via `is_enabled()`.
- `.python-version` (`3.8`) — required so Sublime runs this package on the
  3.8 plugin host; without it the Compass import fails and the plugin
  silently disables itself.
- No top-level Compass imports: the package loads silently when Compass
  is absent and registers in `plugin_loaded()` when present.
- Outgrowing one file? Mirror the bundled plugins: helpers in `utils.py`,
  class + `_PLUGIN_INSTANCE` in `plugin.py`.
'''


class CompassCreatePluginCommand(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return external_plugins_enabled()

    def is_visible(self):
        return external_plugins_enabled()

    def run(self):
        self.window.show_input_panel(
            "Plugin name:", "", self.on_done, None, None
        )

    def on_done(self, name):
        short = sanitize_short_name(name)
        if not short:
            sublime.error_message(
                "Compass: invalid plugin name. Use letters, numbers, spaces, - or _."
            )
            return

        dirname = PLUGIN_PREFIX + short

        plugin_id = to_plugin_id(short)
        if not plugin_id:
            sublime.error_message("Compass: could not derive a plugin id.")
            return

        dest = os.path.join(sublime.packages_path(), dirname)
        if os.path.exists(dest):
            sublime.error_message(
                "Compass: Packages/%s already exists. No files written." % dirname
            )
            return

        class_name = to_class_name(short)
        display = (name or "").strip() or short
        settings_file = short + ".sublime-settings"
        tag = to_tag(short)

        plugin_src = (
            PLUGIN_TEMPLATE.replace("__DISPLAY__", display)
            .replace("__PLUGIN_ID__", plugin_id)
            .replace("__SETTINGS_FILE__", settings_file)
            .replace("__TAG__", tag)
            .replace("__CLASS_NAME__", class_name)
        )
        readme_src = (
            README_TEMPLATE.replace("__DISPLAY__", display)
            .replace("__TAG__", tag)
            .replace("<Short>", short)
        )

        try:
            os.makedirs(dest, exist_ok=False)
            with open(os.path.join(dest, "plugin.py"), "w", encoding="utf-8") as f:
                f.write(plugin_src)
            with open(os.path.join(dest, settings_file), "w", encoding="utf-8") as f:
                f.write(SETTINGS_TEMPLATE)
            with open(os.path.join(dest, "README.md"), "w", encoding="utf-8") as f:
                f.write(readme_src)
            with open(os.path.join(dest, ".python-version"), "w", encoding="utf-8") as f:
                f.write(PYTHON_VERSION + "\n")
        except Exception as e:
            sublime.error_message("Compass: could not create plugin: %s" % e)
            return

        sublime.status_message("Compass: created plugin Packages/%s" % dirname)
        self.window.open_file(os.path.join(dest, "plugin.py"))
