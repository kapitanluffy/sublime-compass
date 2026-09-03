# Compass Navigator — Architecture

## What It Is

A Sublime Text MRU (Most Recently Used) tab switcher. Press `ctrl+tab` to see your open tabs sorted by most recently used, plus unopened project files. Arrow through them with live preview, press Enter to jump.

## Module Map

```
plugin.py                    ← Sublime entrypoint, calls load()
utils.py                     ← Global state (PLUGIN_STATE), settings, debug

src/
  __init__.py                ← Re-export hub, imports everything
  core.py                    ← load() / load_window() — startup initialization
  stack.py                   ← The MRU data structure (STACK) and all operations
  view_stack.py              ← Per-(window, group) facade over STACK
  sheet_group.py             ← SheetGroup: List[Sheet] + focused pointer
  file.py                    ← Simple File(path, folder) data class
  events.py                  ← CompassFocusListener — keeps STACK in sync
  utils.py                   ← View metadata, ripgrep, preview generation, parse_sheet

  commands/
    show.py                  ← CompassShowCommand — the quick panel (main UI)
    move.py                  ← CompassMoveCommand — arrow key handling
    close.py                 ← CompassCloseCommand — close panel with reset flag
    dump_stack.py            ← Debug: print STACK to console
    clear_cache.py           ← Clear compass_stack_cache setting
    index_files.py           ← Reindex: clear cache + reload

  plugins/files/
    file.py                  ← File(file, folder, window) — 3-arg variant with project ID
    stack.py                 ← FILE_STACK — OrderedDict of unopened files + ripgrep
    events.py                ← CompassPluginFilesListener — lifecycle for file plugin
```

## Data Structures

### STACK (the MRU)

`src/stack.py` defines the global MRU:

```python
STACK: List[StackItem]
# where StackItem = Tuple[window_id, group, sheet_ids, focused_id]
```

Each entry represents a **group of tabs** in a specific Sublime group:
- `window_id` — which Sublime window
- `group` — which group within that window (0, 1, 2…)
- `sheet_ids` — list of `sublime.Sheet.id()` values for the tabs in this group
- `focused_id` — the `Sheet.id()` that was active when this entry was pushed

**Order matters:** index 0 is the most recently used. `push_sheets` moves entries to the front.

### SheetGroup

`src/sheet_group.py` — a `List[sublime.Sheet]` with a `.focused` attribute. Used when converting raw STACK tuples into Sublime Sheet objects for `select_sheets()` / `focus_sheet()`.

Created by `convert_stack_to_sheet_group()` in `view_stack.py`.

### FILE_STACK (unopened files)

`src/plugins/files/stack.py` — separate from STACK. An `OrderedDict` keyed by `(file, folder, projectId)`. Populated by `ripgrep --files`. Only shown in the quick panel when `ripgrep_path` is set.

### PLUGIN_STATE

`utils.py` — global dict tracking UI state:
- `is_quick_panel_open` — prevents re-entrant opens
- `highlighted_index` — last highlighted item (for Escape restore)
- `is_reset` — whether Escape should revert to launch view (True) or keep selection (False)

## Startup Flow

```
plugin_loaded()                          [plugin.py]
  ├─ reset_plugin_state()                [utils.py]
  └─ load()                              [src/core.py]
       ├─ for each window:
       │    load_window(window)          [src/core.py]
       │      ├─ hydrate_stack(window)   [src/stack.py]  — restore from cache
       │      └─ append_sheets(...)      [src/stack.py]  — add any sheets not in cache
       └─ CompassPluginFilesListener.on_plugin_loaded()
            └─ parse_listed_files(window)  [src/plugins/files/stack.py]  — ripgrep
```

### hydrate_stack

Reads `compass_stack_cache` from `window.settings()`. For each cached entry:
1. Try to find each sheet by ID (`sublime.Sheet(id)`)
2. If sheet is dead, try matching by filename from the cached file path
3. If still dead, skip the entire entry
4. After filtering, validate that `focused_id` is in the surviving sheets (STR-16 fix)
5. Call `append_sheets` to add valid entries to STACK

## Runtime Flow (User Opens Compass)

```
compass_show                             [show.py: run()]
  ├─ ViewStack.all(group).all()          [view_stack.py]  — get all SheetGroups
  │    └─ convert_stack_to_sheet_group() — STACK tuples → SheetGroup objects
  ├─ CompassPluginFileStack.generate_items(projectId)  — unopened files
  ├─ build QuickPanelItem list
  └─ window.show_quick_panel()
       ├─ on_highlight(index)            — preview (transient open or select_sheets)
       └─ on_done(index)                — final selection
```

### on_done Selection

Two paths depending on item type:

**SheetGroup (open tab):**
```python
window.select_sheets(sheets)     # select the group
window.focus_sheet(focused)      # focus the specific tab (with validation)
```

**File (unopened file):**
```python
CompassPluginFileStack.on_select(item, window)  # window.open_file(path)
```

**Escape / Cancel:**
- `alt+alt` → `compass_close(reset=True)` → sets `is_reset=True`, hides panel → `on_done(-1)` → `index=0` (navigates to MRU head)
- `ctrl+ctrl` → `compass_close(reset=False)` → sets `is_reset=False`, hides panel → `on_done(-1)` → `index=highlighted_index` (keeps selection)

## Event Listener (Keeping STACK in Sync)

`CompassFocusListener` in `src/events.py`:

| Event | Action |
|---|---|
| `on_activated_async` | `push_sheets(window, [view.sheet()], group, focused)` — moves to MRU head. Skips if `is_transient()` or `is_view_valid_tab()` returns True. |
| `on_pre_close` | `remove_sheet(sheet)` — removes from STACK. Closes panel if open. |
| `on_pre_close_window` | `remove_window(window)` — clears all entries for this window. |
| `on_pre_close_project` | `remove_window(window)` — same. |
| `on_load_project_async` | `hydrate_stack(window)` — re-hydrate from cache. |
| `on_query_context` | Returns True for `key == "compass"` — enables keybinding context. |

### is_view_valid_tab

Returns True for views whose `element()` is non-None and not `"find_in_files:output"`. When True, the view is **skipped** (not tracked in STACK). This ignores special panels (settings, console) but DOES track find-in-files output.

### Auto-close Tabs

`cleanup_sheets()` in `events.py` — after each activation, if `max_open_tabs > 0` and sheet count exceeds it, closes the oldest non-dirty, non-scratch sheet.

## Settings

| Setting | Default | Effect |
|---|---|---|
| `debug` | `true` | Print to console |
| `jump_to_most_recent_on_show` | `true` | Pre-select item index 1 (MRU head) on open |
| `ripgrep_path` | `""` | Path to ripgrep; enables `#open` file listing |
| `only_show_unopened_files_on_empty_window` | `true` | Only show file list when window has no sheets |
| `enable_tags` | `false` | Show `#tabs`, `#scratch`, etc. filter tags |
| `preview_on_highlight` | `true` | Preview sheet on arrow |
| `enable_context_preview` | `true` | Show cursor-line context in preview |
| `max_open_tabs` | `1000` | Auto-close oldest tab when exceeded; 0 disables |
| `only_show_items_in_focused_group` | `true` | Only show items from active group |
| `plugins.files.enabled` | `true` | Enable unopened-files plugin |
| `plugins.files.enable_cache` | `false` | Cache ripgrep output |

## Key Design Decisions

1. **Global STACK, per-window slicing:** STACK is a single list. Window/group scoping is done by filtering on `window_id` and `group` at query time. This means `remove_window` must be careful not to mutate during iteration (STR-7 fix).

2. **Cache as serialization:** The STACK is serialized to `window.settings()` as `compass_stack_cache`. This persists across restarts but is throttled to 30s writes. On load, `hydrate_stack` restores from cache with fallback to `build_stack`.

3. **Sheet IDs as identity:** Sheets are tracked by `sublime.Sheet.id()`, not file paths. This handles views without files (scratch, console) but means IDs can go stale when views close.

4. **Two File classes:** `src/file.py` (2-arg) for general use, `src/plugins/files/file.py` (3-arg with project ID) for the file plugin. Both have Windows-only path separators.

5. **Keymap is commented out:** Users must manually enable keybindings via "Preferences: Compass Keybindings". This is intentional — the keymap file in the repo is a template.

## Known Issues

- **STR-5 (fixed):** Startup hydration only hydrating the last window — closure captured wrong variable.
- **STR-6 (fixed):** `load_window` appending sheets with hardcoded `group=0`.
- **STR-7 (fixed):** `remove_window` mutating STACK during iteration.
- **STR-8 (fixed):** `FILE_STACK.clear()` wiping all projects on any window close.
- **STR-16 (fixed):** Stale `focused` pointer causing wrong view focus on selection.
- **STR-9 (canceled):** Escape/cancel behavior — not reproducible, `alt+alt` navigates to index 0 by design.
- **STR-10 (open):** Global ripgrep deduplication across searches.
- **STR-11 (open):** Unify the two File classes into one.
- **STR-12 (open):** Add LineNumber/Point attributes to Viewport.
- **STR-13 (open):** Delete SheetGroup, inline its logic.
- **STR-15 (open):** Move `.sublime-settings` inside the package dir.
