# PERF NOTES R106-IPC (Python<->WebKit bridge)

Earlier pass (R25-IPC) already did: shared JSON encoder in `webview.py`, broadcast serialised once, overview and
dock share one windows payload. This pass looked again at the bridge path and changed only two small things.

## Changes

1. `toplevels.py`: one GLib idle callback per burst of window events.
   Every wlr foreign-toplevel `done` or `closed` event posted its own `GLib.idle_add(self.on_change)`. A terminal
   that retitles itself can send many of these per second. Now a flag (`change_queued`) keeps one callback pending;
   the flag is cleared before the windows are read, so a later event always gets its own callback.
   Measured with a stubbed `gi` (no GTK in this sandbox): 1000 events -> 1 idle callback (before: 1000, one per
   event, by construction of the old code). Enqueue cost 0.18 us per call.
   Output: `windows_changed` still coalesces to one update per 60 ms, so the UI sees the same updates.

2. `universe_shell.py` `windows_update` + `window_list`: the window snapshot is passed on, not taken again.
   `windows_update` took `toplevels.list()`, then `window_list()` took it a second time (copying every window
   dict). `window_list(windows=None)` now accepts the snapshot; `None` keeps the old behaviour for the other callers.
   Measured: copying 8 window dicts takes 0.51 us, 20 takes 1.45 us. Saves one copy per window update, so it is a
   small gain. Checked with a stubbed `window_list`: same output with and without the snapshot.

## Checked and skipped

- `webview.py` `event_code` uses `json.dumps(name)`: that uses the module's default encoder (no new object per call),
  so there is nothing to gain.
- `Bridge.handle` replies through `GLib.idle_add` even for synchronous handlers. Calling `reply` directly would
  change when the page gets the answer (ordering), so skipped.
- `Bridge` threaded handlers: one idle per reply is needed for ordering; skipped.
- `wine.install` progress: only per stage (a few calls per install), not a storm.
- `status_tick`: already sends only on change; `status()` costs (subprocesses every 10 s) belong to the subprocess
  area, not this one.
- `universe_shell.py` ctl socket `json.dumps(..., default=str)`: not on a hot path (command line use only).
- JS side (`api.js`, debouncing of search calls per keystroke): would change timing, so out of scope.

## Risk

- Low for both. Event order and content reaching the pages are unchanged; the only difference is fewer identical
  callbacks in a burst.
- Not run end to end: gi, GTK and Wayland are not available in this sandbox. Verified with `py_compile` and
  stubbed tests only.
