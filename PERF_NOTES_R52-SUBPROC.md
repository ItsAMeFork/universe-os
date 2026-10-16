# PERF_NOTES R52-SUBPROC

## Changes
1. `claude/ai_provider.py` `launch_plan()`: `instructions()` was called twice per launch for the `claude` and `gemini` providers (AGENTS.md/GEMINI.md text and `--append-system-prompt`). Each call re-reads `uitleg.md`, runs a brein sqlite query (`recall` for lessons) and evaluates the plugin catalog. It is now built once per launch and reused.
   - Measured: `instructions()` costs about 0.70 ms per call (dev box, small db); `launch_plan()` now calls it once instead of twice (verified with a call counter), saving about 0.7 ms per launch. Output text is identical, as the inputs are read-only.
   - Risk: very low. The two texts could only differ before if the db or config changed within the few ms between the calls.

## Looked at, skipped
- Everything listed in PERF_NOTES_R5-SUBPROC.md and PERF_NOTES_R29-SUBPROC.md (still true).
- `wine.list_apps()` reads one `app.json` per app, but only on user request from the Windows apps page; a cache would need directory-wide invalidation for no visible gain.
- `ai_provider.load()` / `_read()`: ~10 callers, each once per user action, never in a loop.
- `_attach_mcp` reads `mcp.json` once per launch.
