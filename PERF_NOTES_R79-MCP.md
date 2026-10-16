# PERF_NOTES_R79-MCP

Area: claude/universe_mcp.py, efficientie.py, auto_accept.py, chrome_agent.py, ollama_host.py.
Earlier pass: PERF_NOTES_R21-MCP.md (auto_accept.active()). Not redone.

## Changed
1. `universe_mcp.py`: `recoll_index`, `base64` and `subprocess` are now imported inside the tools that use them
   (`t_find_files`, `t_screenshot`, `t_notify`, `direct_power`) instead of at module load. The server is started once per
   Claude/Codex/Gemini session and most sessions never use these tools.
   - Measured (40 spawns of `python3 -c "import universe_mcp"`): 26.2 ms -> 20.7 ms (-5.5 ms; bare python is 13.2 ms).
   - Checked: `initialize` and `tools/list` over stdio give the same output; each lazy path still resolves its names
     (find_files, screenshot, notify, direct_power reach their normal "tool missing"/"shell unreachable" errors).
   - Risk: very low. Nothing imports `universe_mcp` as a module (only run as a script). First call of those tools
     pays a one-time import of a few ms.

## Looked at, deliberately not changed
- `t_open_app` 0.5 s poll (max 16x): the interval decides when the tool returns, so it is timing-visible.
- `brein` import (~6.6 ms) is needed at load: the tool schema uses `brein.KINDS`.
- `efficientie.py`: transcript parsing runs once per finished task; no loops or waits. `chrome_agent.py`, `ollama_host.py`:
  no polling; the only spawns are the one-shot MCP server and reflect `Popen`.
- `brein.connect()` re-runs schema DDL per connection (outside this area, see R21 notes).
