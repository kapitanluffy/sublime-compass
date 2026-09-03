v3.0.4

Bug fixes
- Fix multi-sheet groups (multi-selected tabs) disappearing from Compass after switching tabs or restarting
- Fix Compass redirecting to the wrong view when the focused tab reference went stale
- Fix files from other projects leaking into the stack in multi-project windows
- Fix only the last open window's stack being restored on startup
- Fix crash when closing a window while iterating the view stack

Features
- Add `stack_cache_throttle` setting (seconds, min 30) to control how often the tab history is saved

Internal
- Remove dead code: unused 2-arg File class, unused ripgrep wrappers, dead StackManager
- Untrack generated files (.pyc, artifacts) from the repository

v3.0.3
- Fix files showing from other projects
- Fix compass constantly caching when changing views
- Fix compass randomly redirecting to wrong buffer when navigating (thanks @MarketHubb)

v3.0.2
No updates right now. Just a version bump to fix this message you are reading right now.
I do apologize for investing little time in Compass 🙇‍♂️

v3.0.1
- Fix CREATE_NO_WINDOW flag not in subprocess for non-window platforms

v3.0.0

This update is generally refactoring the internals
and preparing Compass to support multiple "sources" via plugins

- Add compass caching (disabled by default)
- Rework internals to support plugins
- A lot of bug fixes

v2.2
- Add `only_show_items_in_focused_group` setting. Allows user to show items across groups in a window.
- Fix ripgrep support not working on non-windows platforms
- Fix compass_close does not reset to initial tab properly
- Increase max_open_tabs to 1000

v2.1
- Add setting to toggle previewing when highlighting items
- Add setting to toggle item context previews
- Rename #files filter to #tabs
- Fix #tabs (pka #files) not showing all sheets when grouped
- Add menu items
- Improve dump stack command
- Disable clear cache command
- Add "Show Compass" in command palette
- Weird duplicate items from #tabs filter will not show anymore if disabled
- Fix only_show_unopened_files_on_empty_window setting not working properly when enabled
- Automatically close extra tabs based on max_open_tabs setting

v2.0
- Compass will now cache the stack so it can be loaded again when Sublime restarts
- Filter #empty is now called #scratch
- Filter #type is now removed
- Builds a stack on all existing windows on load in a separate thread
- Fix when closing tabs does not go back to initial tab
