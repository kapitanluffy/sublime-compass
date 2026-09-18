# Creating a Compass plugin

External plugins live in their own package directory and contribute rows
to the Compass quick panel. The fastest path is the scaffold; this guide
explains the contract the scaffold implements.

## Scaffold a plugin

1. Command palette → `Compass: Create Plugin`, enter a name (e.g. `Foo`).
2. Compass writes `Packages/Compass Plugin - Foo/` with:
   - `plugin.py` — lean `foo / bar / baz` sample with per-plugin MRU.
   - `Foo.sublime-settings` — `{ "enabled": true }`.
   - `.python-version` (`3.8`) — Sublime must run the package on the
     3.8 plugin host; without it the plugin silently disables itself.
   - `README.md` — what to delete/replace to make it yours.
3. Restart Sublime (or touch the package) so `plugin_loaded()` runs.

Name rules: short name sanitizes spaces to `-` and must match
`[A-Za-z0-9-_]`; the scaffold refuses to overwrite an existing directory.
The plugin id is `compass_plugin_<short>` (`Foo` → `compass_plugin_Foo`)
and the filter tag is derived from the id (`Foo` → `#foo`).

## The plugin protocol (`src/plugins/plugin_base.py`)

Subclass `CompassPlugin` and implement:

| Method | Role |
|---|---|
| `get_id()` | Stable item type, e.g. `compass_plugin_foo`. Compass stores it in `kind[2]` and routes selection back via `is_applicable`. |
| `get_plugin_tag()` | Filter tag, e.g. `#foo`. Compass **always** prepends it to the trigger (`#foo bar`), regardless of `enable_tags`. |
| `is_enabled()` | Gate. The scaffold reads `"enabled"` from its own settings file. |
| `refresh_cache(window)` | Rebuild whatever `generate_items` reads. Called on every panel open. |
| `generate_items(project_id)` | Return `(details, meta)`. See contract below. |
| `is_applicable(item)` | Claim rows for highlight/select routing (`item.kind[2] == get_id()`). |
| `on_highlight(item, meta, window)` | Preview (transient open). |
| `on_select(item, meta, window)` | Commit. Move the key to the head of `_RECENT` for MRU. |

## Item contract: details dicts, not panel items

`generate_items` returns plain details — Compass builds the
`sublime.QuickPanelItem`. Each detail is a dict:

```python
{"trigger": "bar", "details": "", "annotation": "Foo",
 "kind": (sublime.KindId.COLOR_YELLOWISH, "f")}
```

Only `trigger` is required. Compass prepends `get_plugin_tag()` to the
trigger and sets `kind[2]` to the plugin id and `kind[3]` to the matching
`meta` entry (parallel list, your own objects). Keep panel API usage at
zero: importing `sublime` is fine for `KindId`, but never construct a
`QuickPanelItem` yourself — plugins that return built items still work
via the legacy path, but new plugins must use details dicts.

## Registration: `plugin_loaded()` only

No Compass imports at top level — the package must load (and silently
disable itself) when Compass is absent:

```python
def plugin_loaded():
    global CompassPlugin, COMPASS_AVAILABLE
    try:
        registry_mod = importlib.import_module(
            "Compass Navigator.src.plugins_registry"
        )
    except Exception:
        COMPASS_AVAILABLE = False  # silent: never traceback without Compass
        return
    COMPASS_AVAILABLE = True
    registry_mod.register_plugin(_PLUGIN_INSTANCE)
```

`generate_items` returns `([], [])` while `COMPASS_AVAILABLE` is false,
and `plugin_unloaded()` flips the flag back. Catch broad `Exception`:
a `SyntaxError` from a stale host (see `.python-version` above) must
also disable silently.

## Reacting to Compass events (`src/event_bus.py`)

Subscribe in `plugin_loaded()` after registering:

```python
from Compass Navigator.src.event_bus import subscribe
subscribe("compass_file_focused", _on_compass_file_focused)
```

Compass emits `compass_file_focused` (payload `item_type`, `file`) when a
plugin row is highlighted or selected. There is deliberately no
folder-change event: Sublime exposes no folder-add listener, so folder
diffing was removed as unreliable — do not poll `window.folders()`.

## Verify

- `python -m compileall <package dir>` — syntax (Python 3.8 only).
- Restart Sublime, open Compass, type `#<tag>` — your rows appear as
  `#<tag> <trigger>`.
- Select rows in 3-2-1 order and confirm MRU reorders them.
- Temporarily rename the `Compass Navigator` package and restart:
  the console must stay clean (silent disable).
