# Provenance — Compass Navigator

> Living record for future LLM sessions. Update this file when the codebase, direction, or workflow changes. `AGENTS.md` is the operational instruction file; this file is the historical/strategic context.

**Repo:** `kapitanluffy/sublime-compass` (Package Control name `Compass Navigator` — space matters for `${packages}` paths)  
**Snapshot:** `master@0ce9140` (2025-07-10, tag `3.0.3`), Python `3.8` (`.python-version:1`, Sublime embedded interpreter)  
**Recorded:** 2026-08-30 — no CI, no test suite, no linter; verification is syntactic + manual in Sublime.

---

## 1. What it is

Sublime Text MRU navigator. `plugin.py:1` `plugin_loaded()` → `utils.py:14` `reset_plugin_state()` + `src/core.py:15` `load()`. Replaces `ctrl+tab` with a visual `QuickPanel` ( `src/commands/show.py:24` `CompassShowCommand` ) that shows the most-recently-used sheet stack with tag filtering and optional unopened-file search.

Feature set: MRU stack per `(window.id, group)` (`src/stack.py:32` `STACK`, `src/view_stack.py:21` `ViewStack`, `src/stack_manager.py:5` `StackManager`), filter tags `#tabs/#scratch/#dirty/#search/#groupN/#open` (`src/utils.py:54` `generate_view_meta()`), ripgrep-backed `#open` (`src/plugins/files/stack.py:149` `list_files()`), preview on highlight, LRU auto-close via `max_open_tabs` (`src/events.py:13` `cleanup_sheets()`), project-scoped persistence via `window.settings().get('compass_stack_cache')` (`src/stack.py:130` `cache_stack()`).

## 2. Lineage

- `1.x–2.x` — single global stack + `StackManager`/`ViewStack` evolution (`feat/stack-cache` branch history).
- `3.0` (`e33891b` 2024-10-19, PR #14) — extracted `src/plugins/files/` with separate `FILE_STACK: OrderedDict[(file,folder,projectId),...]` where `projectId = project_file_name or window.id()` (`src/commands/show.py:118`, `src/plugins/files/stack.py:119`), added `plugins.files.enabled/enable_cache` settings, added `compass_index_files`/`compass_clear_cache` commands. Migrated persistence from in-memory only to `compass_stack_cache`.
- `3.0.1–3.0.3` — platform fix (`CREATE_NO_WINDOW` on non-Windows, `bbab062`), cross-project file leakage fix (`1e1960b`), cache-throttle fix (`4208fbc`), index alignment fix (`2b69f97`). Last meaningful commit `2025-07-10`.

## 3. Current state — health

**Works, dormant.** Package Control release `3.0.3` is stable. Maintainer cadence sparse (`CHANGELOG.md:7` apologizes for low investment). No open `gh` CLI in this env; no `messages.json` beyond `3.0.2`.

**Strengths:** Small surface (~15 source files), clear entrypoint, user-visible settings in `Compass Navigator.sublime-settings:1`, keymap is opt-in (`Default.sublime-keymap:1` fully commented — exposed via `Default.sublime-commands:11` `Preferences: Compass Keybindings`).

**Debt / fragility:**
- Global mutable `STACK` + secondary `FILE_STACK`; `ViewStack.all()` rebuilds from `STACK` each call — two sources of truth. Hydration in `src/stack.py:183` `hydrate_stack()` tries `Sublime.Sheet(id)` then filename fallback; `Untitled #N` matching is heuristic (`src/stack.py:160`).
- Duplicate ripgrep impls (`src/utils.py:19` `list_files()` vs `src/plugins/files/stack.py:149`), synchronous `subprocess.run --files` on every `on_plugin_loaded` / `compass_show` when `enable_cache=false` — slow on large projects.
- Stubs not tracked: `src/file_watcher.py:6` `CompassFileEventListener` (only `print` for `FileWatcher:file_watcher_broadcast_event`), `src/plugins_registry.py:2` `COMPASS_PLUGSNS` typo + empty `CompassPluginsRegistry`, `artifacts/*.txt` empty files. All `git ls-files --others` — intentional WIP, not to be committed as-is.
- No automated verification. Only `python -m py_compile plugin.py utils.py` / `python -m compileall src` and manual Sublime reload (symlink repo as `Compass Navigator` into `Packages/`).

**Added in reassessment (2026-08-30, second pass):**
- `src/events.py` actually provides `on_query_context`, `on_pre_close_window`, `on_pre_close_project` in addition to `on_activated_async`/`on_pre_close`/`on_load_project_async` — the earlier event list was incomplete.
- The "find-in-files output is ignored" claim is inverted. `is_view_valid_tab` (`src/events.py:8`) returns True for non-None elements that are **not** `find_in_files:output`, so those panels are skipped and find output is tracked (tagged `#search` in `generate_view_meta`). Re-verify Sublime's `is_transient()` for the find output panel.
- Multi-window/multi-group correctness bugs (not previously flagged):
  - `src/core.py:19` `load()` schedules `set_timeout_async(lambda: load_window(window))` with late-bound `window` — only the **last** open window is hydrated at startup (regression since `507e6f5`).
  - `src/core.py:load_window` appends missing sheets with `group=0` (ignores the real group) and guards on `len(STACK) != len(window.sheets())` using the **global** `STACK` length — wrong when ≥2 windows are open.
  - `src/stack.py:66` `remove_window` mutates `STACK` while iterating, dropping every other block for multi-group windows.
  - `src/plugins/files/events.py` `on_pre_close_window`/`on_pre_close_project` call the **global** `FILE_STACK.clear()`, wiping the file index for *every* project when any window/project closes (undercuts the `1e1960b` project-scoping fix).
- `src/commands/show.py` `on_select(-1)` (Escape/cancel) reset `index` to `0`/`highlighted_index` and **navigated**, so canceling the panel opened a tab; `on_highlight` also raised on `index == -1`.
- Duplicate `File` classes: `src/file.py` (2-arg) vs `src/plugins/files/file.py` (3-arg), both use a Windows-only `"%s\\"` separator for `relative`. `src/utils.py` `generate_files`/`generate_file_per_folder` are dead code and the latter used an **unguarded** `subprocess.CREATE_NO_WINDOW` (POSIX `AttributeError`) — the `bbab062` fix only patched `list_files`.
- Shipped `Compass Navigator.sublime-settings` has `"debug": true` (verbose console for all users); `messages.json` has no `3.0.3` entry.

## 4. Architecture snapshot (for quick ramp-up)

```
plugin.py → src/core.py:load() → src/stack.py:hydrate_stack()/build_stack()
         → utils.py:PLUGIN_STATE {is_quick_panel_open, highlighted_index, is_reset}
src/events.py:CompassFocusListener (on_activated_async→push_sheets, on_pre_close→remove_sheet, on_load_project_async→hydrate)
src/commands/show.py:CompassShowCommand (builds QuickPanelItem list from ViewStack + FILE_STACK + metadata alignment)
src/plugins/files/stack.py:CompassPluginFileStack (push/append/generate_items/is_applicable/on_highlight/on_select via kind[2]==ITEM_TYPE)
```

Tags only emit when `enable_tags==true`. `only_show_items_in_focused_group`, `jump_to_most_recent_on_show`, `only_show_unopened_files_on_empty_window` control `show.py:32` grouping/selection. `max_open_tabs=0` disables `cleanup_sheets`.

Relative imports only (`from .utils import *`) — will not run outside Sublime; `sublime`/`sublime_plugin` are host-provided.

## 5. Future — where this is headed

**Explicit direction in branches (not yet on `master`):**
- `refactor/rework-compass` (`da6e7cf`) + `feat/mru-plugin` — extract MRU itself to `src/plugins/mru/` (344-line `stack.py`), genericize plugin system so tabs/files/bookmarks/move-lines are interchangeable quick-panel sources. `feat/jump-bookmarks` adds `src/plugins/bookmarks/` (events+stack), `feat/move-lines` adds `move_line` command.
- `FileWatcher` integration — stated fix for stale `#open` ( `README.md:110` ), currently stub. Intent is incremental `FILE_STACK` update on `create/change/delete` instead of full `parse_listed_files` scan.
- `feat/stack-cache` history shows earlier persistence attempt; `feat/index-files` (`67961f3`) is already merged into `3.0`.

**If continuing this project:**
1. Finish `mru` plugin extraction (makes `STACK` mockable/testable outside Sublime).
2. Wire `FileWatcher` broadcast to incremental `FILE_STACK` mutation (vs. current `CompassIndexFilesCommand:6` `erase + load()` full reindex).
3. Promote `STACK_EXPIRY_TIME=30` (`src/stack.py:42` `@todo`) to setting, deduplicate `list_files`, add `compileall` CI.
4. Keep `Default.sublime-keymap` commented; don't break Package Control `messages.json` contract.

**Risk if not:** Stagnation. Without plugin abstraction + watcher + minimal test harness, next Sublime API or ripgrep behavioral change will regress hydration/project-scoping (already fixed twice in `3.0.x`).

## 6. How to continue with LLMs

- Read `AGENTS.md` first (operational quirks), then this file (strategic context).
- Prefer reading `src/stack.py`, `src/commands/show.py`, `src/plugins/files/stack.py`, `src/events.py` to re-derive execution flow — don't trust prose over those files.
- When adding a new source, follow `src/plugins/files/` pattern (`FILE_STACK` + `FilePluginItem` + `is_applicable/on_highlight/on_select` via `kind` tuple injection).
- Update this file's Snapshot/Lineage when branching or releasing; delete this note when self-evident.

---

## 7. Reassessment addendum (2026-08-30, second LLM pass)

A second independent pass re-read every source file and cross-checked against this record. The strategic read (dormant, small surface, no tests, refactor-wanted) holds, but the prior pass **under-scanned multi-window/multi-group correctness** and carried one factual error (find-in-files output handling — see Debt above). Net: same architecture verdict, but the highest-value fixes are `core.py` startup-hydration closure, the global `FILE_STACK.clear()` on window close, and the Escape-opens-a-tab `on_select` behavior. These are documented, not yet patched (code changes were out of scope for this pass).
