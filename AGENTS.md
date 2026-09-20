# AGENTS.md

## Project
Sublime Text plugin (Python 3.8 per `.python-version`, runs inside Sublime's embedded interpreter - not standalone). Package dir name is `Compass Navigator` (space matters for `${packages}` paths). No build/test/lint toolchain, no package manager.

## Workflow: Plan first, checkpoint every commit and push
- On every prompt, provide a high-level overview of your plan before doing anything.
- Do NOT edit files, run commands, or otherwise implement until the user gives explicit approval (e.g. "Go", "proceed", "yes").
- Surface commit checkpoints: before EVERY `git commit`, show the exact staged changes (`git status --short` + `git diff --cached`) and the proposed commit message, then wait for explicit "Go". Approval of a plan does NOT carry over to approval of its commits.
- Stage only what the approved plan called for; never sweep in unrelated WIP/untracked files.
- Before creating a tag or running `git push`, surface the commits/refs/tags that will go out and wait for explicit approval.
- If a tag or commit must be rewritten after the fact (amend, rebase, re-tag, move branch pointer), surface the plan and get approval first — moved tags affect anyone who already pulled.
- If the plan involves multiple options or ambiguity, surface the choices with your recommendation and let the user decide.
- After approval, implement and verify, then report back concisely; continue any follow-up work only when the plan covered it or the user asks.
- Never state facts without a reference or evidence. If an assumption is needed, explicitly say so and explain why.

## Structure
- `plugin.py` - entrypoint: `plugin_loaded()` -> `reset_plugin_state()` (`utils.py`) + `load()` (`src/core.py`)
- `utils.py` - global `PLUGIN_STATE` (`is_quick_panel_open`, `highlighted_index`, `is_reset`), `plugin_settings()`, `plugin_debug()`
- `src/__init__.py` - re-exports everything; `src/core.py` hydrates `STACK` on load via `hydrate_stack()` / `build_stack()`
- `src/stack.py` - `STACK: List[Tuple[window_id, group, sheet_ids, focused_id]]` + `STACK_UPDATE_TIME`; cached to `window.settings().set('compass_stack_cache', ...)`. Cache write throttle read from `stack_cache_throttle` setting (min 30, default 30).
- `src/view_stack.py` - `ViewStack` is a per-`(window.id, group)` facade over global `STACK`
- `src/sheet_group.py` - `SheetGroup(List[Sheet])` with `.focused`
- `src/events.py` - `CompassFocusListener` (`on_activated_async`, `on_pre_close`, `on_pre_close_window`, `on_pre_close_project`, `on_load_project_async`, `on_query_context`). A view is skipped (not pushed/removed from the stack) when `sheet.is_transient()` is True OR `should_skip_view(view)` is True, where `should_skip_view` returns True for views whose `element()` is non-None and not `"find_in_files:output"`. So find-in-files output (`element()=="find_in_files:output"`) is NOT ignored — it is tracked and tagged `#search` in `generate_view_meta`; other special panels (non-None element) are ignored. Re-verify Sublime's real `is_transient()` behavior for the find output panel.
- `src/event_bus.py` - in-process subscribe/emit bus. `subscribe(event, handler)` / `emit(event, **payload)`. Compass emits `compass_file_focused` (payload `item_type`, `file`) from `show.py` when a plugin item is highlighted or selected, and `compass_folders_changed` (payload `window`) from `check_folders_changed()` (`src/events.py`, called on activation) when the window folder list changes. No folder-add listener from Sublime itself (GH #4753, #2234): detection is a cheap core-owned folder-list snapshot, not ripgrep walks or timer polls — do not re-add folder diffing without owner approval.
- `src/commands/` - `compass_show` (`show.py`), `compass_move`, `compass_close`, `compass_index_files`, `compass_dump_stack`, `compass_clear_cache`
- `src/plugins/files/` - separate `FILE_STACK: OrderedDict[(file,folder,projectId), tuple]`; filtered by `projectId = project_file_name or window.id()`
- `src/utils.py` - `list_files()` shells `ripgrep --files`, `generate_view_meta()`/`parse_sheet()` for tags/kind
- `Compass Navigator.sublime-settings` / `Default.sublime-commands` / `Default.sublime-keymap` / `Main.sublime-menu`

## Execution Quirks
- Relative imports only (`from .utils import *`, `from .src import *`) - will not import/run outside Sublime; `sublime`/`sublime_plugin` are host-provided. Gotcha: `dict_deep_get` lives in `src/utils.py`, so from `src/plugins/*/` it is `...utils` — NOT `....utils` (that is the top-level `utils.py`). `KindId` color constants use the `...ISH` suffix (e.g. `COLOR_YELLOWISH`).
- `Default.sublime-keymap` is entirely commented out. Users must enable via `Preferences: Compass Keybindings` command. Don't uncomment in repo.
- Settings-driven: `debug` (default false; enable for `plugin_debug` output), `enable_tags`, `ripgrep_path`, `only_show_items_in_focused_group`, `jump_to_most_recent_on_show`, `max_open_tabs` (0=disable auto-close), `stack_cache_throttle` (min 30), `plugins.files.enabled`/`enable_cache`. Tags only emit when `enable_tags==True`.
- MRU logic: `push_sheets` moves to head of `STACK`; `cache_stack()` saves the window cache. Called throttled (30s, `stack_cache_throttle` setting, min 30) from `on_activated_async` (tab switch), and forced (`force=True`) from `show.py:on_done` (compass close) and `ViewStack.remove` (tab close). Groups are preserved because `push_sheets` operates on the full `selected_sheets_in_group` set.
- Untracked WIP: `artifacts/` is not tracked. Tracked but dormant: `src/file_watcher.py` (stub `CompassFileEventListener` for `FileWatcher` broadcast). The plugin registry is real: `src/plugins_registry.py` (`register_plugin` / `get_plugins`).

## Verification (no test suite exists)
- Syntax: `python -m py_compile plugin.py utils.py` or `python -m compileall src` — checks for syntax errors in all .py files. Run this after every code change.
- Manual: symlink/clone repo as `Compass Navigator` into Sublime `Packages/` dir, restart Sublime, `compass_show` via `ctrl+tab` (after enabling keymap), check console for `plugin_debug` (requires `"debug": true`).
- No CI workflows, no pre-commit hooks.

## Conventions
- Python 3.8 syntax only.
- Keep executable source of truth over docs; do not add generic lint/test scaffolding not already present.
- Evergreen docs: when changing code behavior, update the relevant doc in `docs/` in the same changeset.
- State snapshot: `artifacts/STATE.md` (untracked — never commit) is the current-state snapshot. Refresh it on every landing (commit or merge): branch + HEAD, what changed, what's next, Linear issue statuses, and anything unpushed.

## Linear
- Team **Strawhats**. Full workflow: `artifacts/linear-workflow.md` (untracked).
- Issue conventions: bugs get a "How to Reproduce" section; features/refactors get a plan/RFC in the body or a linked spec doc; plugin-system work goes to the **Compass Navigator Plugins** project with explicit Blocked-by links.
