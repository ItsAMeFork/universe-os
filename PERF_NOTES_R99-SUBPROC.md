# PERF_NOTES R99-SUBPROC

## Changes
1. `claude/plugins.py` `public_list()`: it called `_saved()` once per catalog item (about 20 times in total with the `enabled()` calls). Each call ran `_config_path()`, which does an `os.makedirs` plus env and path work, and then deep-copied the entry. The items dict is now read once per call (`_saved_in(items, id)`, `_enabled_in(row, saved)`). `enabled()` and `_saved()` keep their signatures and results.
   - Measured (8-config comparison, see below): `public_list()` 110.8 us -> 10.4 us (about 10x). It runs inside `ai_provider.public_status()`, so that call drops by roughly 0.1 ms; cProfile on `public_status()` showed `plugins.public_list` as its largest part.
   - Verified: old (HEAD) and new `public_list()`, `enabled()`, `mcp_servers()` and `skill_line()` return identical results for: no config file, corrupt JSON, a JSON list, `items` as a list, `items[x]` as a string, `aan` true/false/0, and a missing `status`.
   - Risk: very low. Same file read and same cache (`_read_shared`, keyed on mtime/size/inode). Only difference: `public_list()` now does one stat instead of about 20. The `makedirs` side effect of reading the config is kept in `_config_path()`.

## Looked at, skipped
- Everything in PERF_NOTES_R5-, R29-, R52-SUBPROC.md and R88-SUBPROC.md is still true; those items are not repeated here.
- `ai_provider.public_status()` `installed()` (6 `shutil.which` per call, about 0.2 ms): it cannot be cached, because the AI page relies on it to see a CLI installed during the session.
- `ai_provider.has_key()` (keyring D-Bus call per provider per status): a cache would show stale "key saved" state after an external change in the keyring. Not clearly behaviour-neutral, so skipped.
- `screen.available()` tries `import evdev` on every call when `/dev/uinput` exists. A failed import is not cached by Python. Caching it would miss a driver installed mid-session, so skipped.
- `wine.support()` spawns `wine --version` (called on the Windows page and per file check). It runs only on user actions, and this box has no Wine, so the gain could not be measured. A cache keyed on the Wine binary path and mtime would be safe, but the gain is unmeasured, so skipped.
- `control_center._screen_status_for_ui()` spawns `universe-ctl` (the shell is the authority for screen state); `claude_status()` spawns `claude --version` but no UI code calls `claude.status` in this repo; `_download_dir()` (`xdg-user-dir`) runs only on `brein.export`. All are user-triggered or the value is needed fresh, so skipped.
- `recoll_index.search()` runs `ensure_config()` per query, which is one `os.path.exists`. `folders()` spawns 6 `xdg-user-dir` calls, but only when `recoll.conf` is missing. Skipped.
- `ai_provider._read()`, `accounts._read_clients()`, `brein` reads: about 10 calls per user action, not in loops (`ai_provider.load()` is about 11 us).

## Checks
- `python3 -m py_compile claude/plugins.py`: OK.
- Output comparison script: run in a temp HOME, not committed.
- Not run: `ruff` and `pyflakes` are not installed on this box, so no lint pass. `docs/tests/ai-leren.py` (uses `plugins`) was not run.
