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
| `on_load()` | One-time setup: subscribe to events, kick off background work. No-op by default; called once by `load_plugins()` — never call it yourself. |
| `on_unload()` | Tear down whatever `on_load` set up. No-op by default. |
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

## Disabling external plugins

Third-party plugins load only when `flags.plugin_support.enabled` is
`true` (default `false`). Bundled plugins always run. The gate applies
everywhere `get_plugins()` is consumed — panel rows, highlight/select
routing, and `on_load` — so flipping it takes effect on the next panel
open, no restart. `Compass: Create Plugin` refuses with an explanation
while the gate is off. What counts as bundled is decided by Compass
core (hardcoded ids in `src/plugins_registry.py`) — plugins cannot
declare themselves bundled.

## Lifecycle: register → `on_load` → per-open → `on_unload`

1. **Register** — `plugin_loaded()` calls `register_plugin(instance)`.
   Re-registering an id replaces the entry, so reloads never duplicate
   rows. Bundled plugins register at import time, hence always first.
2. **`on_load`** — `core.load()` calls `load_plugins()` once per
   session: in registration order, skipping `is_enabled() == False`,
   each `on_load` isolated by try/except so one broken plugin can't
   block the rest.
3. **Per panel open** — `refresh_cache(window)` then
   `generate_items(project_id)`; `on_highlight` / `on_select` route by
   `is_applicable`.
4. **`on_unload`** — release whatever `on_load` set up.

## Recent-picks pattern

Each section owns its own ordering — core never reorders your rows.
To float picked items first within your section, use the shared helper
in `src/plugins_registry.py`:

- In `on_select`, call `record_selection(get_id(), key)` with the same
  key you emit in `generate_items` (namespace it yourself, e.g. include
  the project id). Record selects only, never highlights.
- In `generate_items`, wrap your keys with
  `order_by_recent(get_id(), keys)` before building details.

History is per plugin id, capped at `max_recent_picks`, in-memory
only (`false` disables recency entirely). Stale keys (deleted files) are skipped, never stat'ed. Files
(`#open`) is the reference implementation: recent rows float first and
carry a `files · recent` annotation. Note `#open` also matches open-tab
rows, which always precede plugin rows — recents top their own section,
not the whole list.

## Reacting to Compass events (`src/event_bus.py`)

Subscribe in `plugin_loaded()` after registering (via the already
imported `bus_mod` — no direct Compass imports):

```python
bus_mod.subscribe("compass_file_focused", _on_compass_file_focused)
```

def _on_compass_file_focused(item_type, file):
    _status("saw focus: %s" % (item_type,))
```

## What events can I subscribe to?

Two. Compass keeps the bus deliberately small:

| Event | Payload | Fired when |
|---|---|---|
| `compass_file_focused` | `item_type` (plugin id), `file` (path string, or `None` when the meta isn't a path) | A plugin row is highlighted (`show.py:on_highlight`) or selected (`show.py:on_done`). Fires only for rows a plugin claims via `is_applicable`. |
| `compass_folders_changed` | `window` (the Sublime window whose folders changed) | Core's folder-list snapshot (`events.py:check_folders_changed`, called from `CompassFocusListener.on_activated_async`) sees a delta. Files subscribes and re-scans. Handlers run on the activator's thread — keep them cheap and push slow work async. |

Notes:

- Handlers run synchronously on the calling thread — keep them cheap
  (status messages, cache flags), never block on subprocess or disk scans.
- `subscribe` dedupes: registering the same handler twice is a no-op.
- There is deliberately no richer folder event: Sublime exposes no
  folder-add listener, so detection is a cheap core-owned folder-list
  snapshot — do not poll `window.folders()` on a timer.

## Verify

- `python -m compileall <package dir>` — syntax (Python 3.8 only).
- Restart Sublime, open Compass, type `#<tag>` — your rows appear as
  `#<tag> <trigger>`.
- Select rows in 3-2-1 order and confirm MRU reorders them.
- Temporarily rename the `Compass Navigator` package and restart:
  the console must stay clean (silent disable).
