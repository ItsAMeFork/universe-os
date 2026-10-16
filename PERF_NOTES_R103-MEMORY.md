# PERF_NOTES_R103-MEMORY — memory footprint of the Python shell (fifth pass)

## Changes
1. `shell/backend.py` `_file_index()`: the name index (up to 60,000 entries) was kept after its 60 s freshness window until the
   next search, so about 10 MB stayed in memory for the rest of the session after one search. A one-shot
   `GLib.timeout_add_seconds(61, ...)` now frees it, armed when the index is built. `_drop_file_index(stamp)` only drops the
   index that armed it (a newer index has its own timer), so a fresh index is never removed early.
   - Measured (tracemalloc, `HOME=/usr`, default 60,000-entry cap): index held 9.8 MB; after the timer fires 0.0 MB (9.8 MB freed).
   - Behaviour: `search_files()` only rebuilds when the index is older than 60 s, as before, so results are identical. The running
     search holds its own reference, so a drop during a search cannot break it. Behaviour checked with a stubbed `gi` (not live):
     index reused inside 60 s with no extra timer; timer drops it; an older timer does not drop a newer index.
   - Cost: one extra main-loop timer per index build. The index is built only by a user search (start menu, Claude search), so
     this is one wakeup per search, not a periodic wakeup.
   - Risk: low. The only way the change can show is a search after 61 s, which already rebuilt the index before this change.

## Looked at, NOT changed
- `_folded` (`backend._folded_apps`): keeps the previous app list alive until the next search. It is a few hundred small dicts;
  a fix would change the identity check that decides when to re-fold, so skipped.
- `windows_apps` / `control_center` windows: kept as `self.window` / `self.view`. These are GTK applications that quit when their
  last window closes, so the references go with the process. No retained WebViews found.
- `claude_ui` terminal (`self.term`): kept on purpose (the session survives hiding the panel); it is freed when the child exits (`term = None`).
- `toplevels.windows/handles/hidden_by_us`: removed on the `closed` event. `buddy_hints.monitors` / `shown_today`: bounded (R44).
- `brein._schema_seen` (one key per database path), `plugins._read_cache` (one entry), `accounts._flows/_states/_servers`
  (pruned since R70): bounded.
- `universe_shell.worlds`: one WebView per monitor, removed on monitor removal (R9).
- VTE scrollback size, WebKit cache settings: would reduce memory but change visible behaviour, so out of scope.

## Tested
- `python3 -m py_compile shell/backend.py`: OK.
- Stubbed-`gi` behaviour check and tracemalloc measurement, run from `/tmp` (not in the repo).
- Not tested: live shell session (no `gi`/display here) and `ruff` (not installed).
