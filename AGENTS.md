# AGENTS.md

## Project
Sublime Text plugin (Python 3.8 per `.python-version`, runs inside Sublime's embedded interpreter - not standalone). Package dir name is `Compass Navigator` (space matters for `${packages}` paths). No build/test/lint toolchain, no package manager.

## Workflow: Plan first, then wait for explicit "Go"
- On every prompt, provide a high-level overview of your plan before doing anything.
- Do NOT edit files, commit, run commands, or otherwise implement until the user gives explicit approval (e.g. "Go", "proceed", "yes").
- If the plan involves multiple options or ambiguity, surface the choices with your recommendation and let the user decide.
- After approval, implement and verify, then report back concisely; continue any follow-up work only when the plan covered it or the user asks.
- Never state facts without a reference or evidence. If an assumption is needed, explicitly say so and explain why.

## Structure
- `plugin.py` - entrypoint: `plugin_loaded()` -> `reset_plugin_state()` (`utils.py`) + `load()` (`src/core.py`)
- `utils.py` - global `PLUGIN_STATE` (`is_quick_panel_open`, `highlighted_index`, `is_reset`), `plugin_settings()`, `plugin_debug()`
- `src/__init__.py` - re-exports everything; `src/core.py` hydrates `STACK` on load via `hydrate_stack()` / `build_stack()`
- `src/stack.py` - `STACK: List[Tuple[window_id, group, sheet_ids, focused_id]]` + `STACK_UPDATE_TIME`/`STACK_EXPIRY_TIME=30s`; cached to `window.settings().set('compass_stack_cache', ...)`
- `src/view_stack.py` - `ViewStack` is a per-`(window.id, group)` facade over global `STACK`
- `src/sheet_group.py` - `SheetGroup(List[Sheet])` with `.focused`
- `src/events.py` - `CompassFocusListener` (`on_activated_async`, `on_pre_close`, `on_pre_close_window`, `on_pre_close_project`, `on_load_project_async`, `on_query_context`). A view is skipped (not pushed/removed from the stack) when `sheet.is_transient()` is True OR `should_skip_view(view)` is True, where `should_skip_view` returns True for views whose `element()` is non-None and not `"find_in_files:output"`. So find-in-files output (`element()=="find_in_files:output"`) is NOT ignored — it is tracked and tagged `#search` in `generate_view_meta`; other special panels (non-None element) are ignored. Re-verify Sublime's real `is_transient()` behavior for the find output panel.
- `src/commands/` - `compass_show` (`show.py`), `compass_move`, `compass_close`, `compass_index_files`, `compass_dump_stack`, `compass_clear_cache`
- `src/plugins/files/` - separate `FILE_STACK: OrderedDict[(file,folder,projectId), tuple]`; filtered by `projectId = project_file_name or window.id()`
- `src/utils.py` - `list_files()` shells `ripgrep --files`, `generate_view_meta()`/`parse_sheet()` for tags/kind
- `Compass Navigator.sublime-settings` / `Default.sublime-commands` / `Default.sublime-keymap` / `Main.sublime-menu`

## Execution Quirks
- Relative imports only (`from .utils import *`, `from .src import *`) - will not import/run outside Sublime; `sublime`/`sublime_plugin` are host-provided.
- `Default.sublime-keymap` is entirely commented out. Users must enable via `Preferences: Compass Keybindings` command. Don't uncomment in repo.
- Settings-driven: `enable_tags`, `ripgrep_path`, `only_show_items_in_focused_group`, `jump_to_most_recent_on_show`, `max_open_tabs` (0=disable auto-close), `plugins.files.enabled`/`enable_cache`. Tags only emit when `enable_tags==True`.
- MRU logic: `push_sheets` moves to head of `STACK`; `cache_stack()` saves the window cache. Called throttled (30s, `STACK_EXPIRY_TIME`) from `on_activated_async` (tab switch), and forced (`force=True`) from `show.py:on_done` (compass close) and `ViewStack.remove` (tab close). Groups are preserved because `push_sheets` operates on the full `selected_sheets_in_group` set.
- Untracked WIP: `src/file_watcher.py` (stub `CompassFileEventListener` for `FileWatcher` broadcast) and `src/plugins_registry.py` (empty `CompassPluginsRegistry`). `artifacts/` is not tracked.

## Verification (no test suite exists)
- Syntax: `python -m py_compile plugin.py utils.py` or `python -m compileall src` — checks for syntax errors in all .py files. Run this after every code change.
- Manual: symlink/clone repo as `Compass Navigator` into Sublime `Packages/` dir, restart Sublime, `compass_show` via `ctrl+tab` (after enabling keymap), check console for `plugin_debug` (requires `"debug": true`).
- No CI workflows, no pre-commit hooks.

## Conventions
- Python 3.8 syntax only.
- Keep executable source of truth over docs; do not add generic lint/test scaffolding not already present.
- Evergreen docs: when changing code behavior, update the relevant doc in `docs/` in the same changeset.
