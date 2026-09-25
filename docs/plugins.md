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
| `on_load()` | One-time setup: kick off background work. No-op by default; called once by `load_plugins()` — never call it yourself. |
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
open, no restart. `Compass: Create Plugin` is hidden from the command
palette while the gate is off. What counts as bundled is decided by Compass
core (hardcoded ids in `src/plugins_registry.py`) — plugins cannot
declare themselves bundled.

Compass ships two bundled plugins, rendered in this section order
(`_BUNDLED_ORDER` in `src/plugins_registry.py`):

- MRU tabs (`compass_plugin_mru_tabs`, no tag) — open-tab rows read from
  core's STACK via `ViewStack`. Storage, caching, and resurrection stay
  in core; the plugin owns row-building, preview, and focus.
- Unopened files (`compass_plugin_file_open_file`, `#open`) — ripgrep
  results from its own `FILE_STACK`.

## Lifecycle: register → `on_load` → per-open → `on_unload`

1. **Register** — one call for everyone: `register_plugin(instance)`.
   External plugins call it in `plugin_loaded()`; bundled plugins call
   it at import time (same call, no separate path — bundled just means
   pre-included, no install needed). Re-registering an id replaces the
   entry, so reloads never duplicate rows.
2. **`on_load`** — `core.load()` calls `load_plugins()` once per
   session: every plugin runs `on_load` bundled-first, skipping
   `is_enabled() == False`, each isolated by try/except so one broken
   plugin can't block the rest. Bundled-first is structural
   (`get_plugins()` partitions), never dependent on import order.
3. **Per panel open** — `refresh_cache(window)` then
   `generate_items(project_id)`; `on_highlight` / `on_select` route by
   `is_applicable`.
4. **`on_unload`** — release whatever `on_load` set up (Files clears
    its stack). Broadcast hooks need no teardown: Sublime owns the
    listener lifetime, and the `_LOADED` guard keeps `load_plugins()`
    single-run within a session.

## Who watches the folders

Core owns folder-change detection: a cheap folder-list snapshot taken
on activation, dispatching `folders_changed` on delta. Plugins
may read the snapshot (`check_folders_changed`) for the per-open check
and post-scan bookkeeping — sanctioned reads, not polling. Never run
your own folder-watching: no ripgrep walks outside a detected change,
no timer polls.

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

## Reacting to Compass events

Override the `on_*` methods on your plugin class — Compass calls them
directly (`dispatch_event`), bundled and external alike. No imports,
no subscriptions:

```python
def on_file_focused(self, window, item_type, file):
    ...
```

Payloads carry live objects (`window`, `sheet`). A second path exists
for packages outside Compass: every event also runs the no-op
`compass_broadcast_event` window command with a JSON payload, which any
package can snoop via `on_window_command` with zero Compass imports.
The command string is the contract — hardcode it, never rename it.
Outsiders get ids instead of objects (`window_id`, `sheet_id`).

| Event | `on_*` payload | Broadcast payload | Fired when |
|---|---|---|---|
| `file_focused` | `item_type`, `file` (path or `None`) | same | A plugin row is highlighted or selected. Only for rows a plugin claims via `is_applicable`. |
| `folders_changed` | `window` | — (`window` is implicit) | Core's folder-list snapshot sees a delta. Files re-scans. |
| `sheet_activated` | `sheet`, `group` | `sheet_id`, `group` | A vetted tab switch: not transient, not skipped, panel closed. May fire on a worker thread. |
| `sheet_closed` | `sheet` | `sheet_id` | A vetted tab close. |
| `window_closed` | `window` | — | Window pre-close. |
| `project_closed` | `window` | — | Project pre-close. |
| `project_loaded` | `window` | — | Project load. |

Notes:

- Handlers run synchronously on the calling thread — keep them cheap
  (status messages, cache flags), never block on subprocess or disk scans.
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
