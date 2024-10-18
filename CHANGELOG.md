v2.2.2
- Fix compass_close does not reset to initial tab properly
- Increase max_open_tabs to 1000

v2.2
- Add `only_show_items_in_focused_group` setting. Allows user to show items across groups in a window.
- Fix ripgrep support not working on non-windows platforms

v2.1.3
- Automatically close extra tabs based on max_open_tabs setting

v2.1.2
- Weird duplicate items from #tabs filter will not show anymore if disabled
- Fix only_show_unopened_files_on_empty_window setting not working properly when enabled

v2.1.1
- Add menu items
- Improve dump stack command
- Disable clear cache command
- Add "Show Compass" in command palette

v2.1
- Add setting to toggle previewing when highlighting items
- Add setting to toggle item context previews
- Rename #files filter to #tabs
- Fix #tabs (pka #files) not showing all sheets when grouped

v2.0
- Compass will now cache the stack so it can be loaded again when Sublime restarts
- Filter #empty is now called #scratch
- Filter #type is now removed
- Builds a stack on all existing windows on load in a separate thread
- Fix when closing tabs does not go back to initial tab
