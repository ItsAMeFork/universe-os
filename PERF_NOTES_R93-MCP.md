# PERF_NOTES_R93-MCP

Area: claude/universe_mcp.py, efficientie.py, auto_accept.py, chrome_agent.py, ollama_host.py.
Earlier passes: PERF_NOTES_R21-MCP.md, PERF_NOTES_R79-MCP.md. Not redone.

## Changed
1. `universe_mcp.py`: `socket` is imported inside `shell()` and `notify_shell()` (its only two users) instead of at load.
   Sessions that only use the brein tools never touch the shell socket.
   - Measured (60 spawns of `python3 -c "import universe_mcp"`, median): ~20.2 ms -> ~18.7-20.0 ms; `-X importtime` shows
     `socket` at ~2 ms cumulative. Gain is small and within noise on this box.
   - Checked: `initialize` + `tools/list` output byte-identical (md5) to HEAD; an unreachable shell still returns the same
     "niet bereikbaar" tool error.
   - Risk: very low. The first shell tool call pays a one-time import of `socket` (~1 ms).

## Looked at, deliberately not changed
- `t_open_app` 0.5 s poll: timing-visible (when the tool returns).
- With `.pyc` present, `brein` costs only ~1.7 ms; the rest of startup is stdlib (`json`, `re`, `enum`) that cannot be dropped.
- `efficientie.py`, `auto_accept.py`, `chrome_agent.py`, `ollama_host.py`: no sleeps or polling; only one-shot spawns
  (reflect `Popen`, MCP server `Popen`). Nothing meaningful left.
