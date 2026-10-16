# PERF_NOTES_R97-UIJS — WebKit UI JS (except world.js)

Rule: no visible or behavioural change. Checked with `node --check` and a node bench; no browser was available
(Playwright MCP failed to connect), so nothing was run in WebKit.

## Changes
1. `planets-hq.js` `planetRows()` (rocky planets, per pixel)
   - Every pixel ran `Math.acos` for all 14 craters. `acos` is decreasing, so a pixel whose dot product with the crater
     centre is below `cos(1.25 r) - 1e-9` can never satisfy `dist < 1.25 r`. That case now `continue`s before the `acos`.
     The threshold is precomputed per crater. The margin keeps the test conservative, so the result is exact.
   - Measured (node, 8 seeds, 320 px, rock): 664 ms -> 592 ms (~11 %). Output compared with `Object.is` over every
     element of the image buffer: identical.
   - Risk: near zero (same pixels; only skipped work).

## Re-checked, NOT changed
- `brein-nevel.js`: loop is a 100 ms timeout chain that stops when `motionOn()` is false (hidden / motion off);
  observers and listeners are removed in the teardown. Further savings in `paint()` would be a few allocations.
- `dock.js`, `panel.js`: render only when the shown data changed; panel has a single 15 s interval.
- `performance.js` fps loop only runs with `?fps=1`; `motion.js` ends by timer; `globe.js`/`planets-hq.js` rAF slices stop
  when the queue is empty.
- `start.js`, `overview.js`, `windows.js`, `ai-ui.js`: event-driven, listeners attached to elements that are replaced
  together with them (no leak); no timers or loops.
