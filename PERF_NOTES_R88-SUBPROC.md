# PERF_NOTES R88-SUBPROC

## Changes
1. `claude/screen.py` `status()`: it called `available()` once and then again inside each `backend_for()` call (up to 4 probes: `os.path.exists`, up to 4 `shutil.which`, plus a retried `import evdev` when `/dev/uinput` exists). `backend_for()` gets an optional `present=` argument and `status()` passes the result it already has. The mouse backend is also computed once instead of twice. Output is identical.
   - Measured (dev box, no input tools): `status()` 147 us -> 41 us; `available()` calls per `status()` 4 -> 1 (verified with a call counter). On a box with ydotool/evdev the saved work is larger (more `which` stats and import attempts).
   - Risk: very low. The probes could only differ before if a tool appeared/disappeared within microseconds. `backend_for(kind, have)` callers are unchanged (new arg defaults to None).

## Looked at, skipped
- Everything in PERF_NOTES_R5/R29/R52-SUBPROC.md (still true: wine.support(), control_center spawns, ai_provider/accounts reads, wine.list_apps).
- `ai_provider.bin_for`/`public_status`: only `shutil.which` stats, one pass per provider, no spawns.
- `_attach_mcp` mcp.json read: once per launch.
