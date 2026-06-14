# Autonomous Game-Studio Progress Log

Append one entry per cycle (newest at the bottom). For the morning review: read top-to-bottom,
each entry = one verified change on branch `autonomous/game-studio`.

Format: `- [cycle N] <what changed> — tests: <pass/fail> — commit <hash>`

---

- [cycle 0] Set up autonomous framework: branch `autonomous/game-studio`, roadmap
  (`docs/GAME_STUDIO_ROADMAP.md`), this progress log. Goal: incrementally grow the autopilot into a
  capable game-studio system overnight, on a branch, with `pytest` gating every change. — setup
- [cycle 1] P0 over-creation fix: repeated-tool-call guard in the ollama/cloudflare loops
  (`orchestrator.py`) — model repeating the same tool-call set now stops instead of spinning to
  max-iterations (this is the "10 spheres" bug we hit live). Added 2 tests. — tests: 34 passed
- [cycle 2] P1 layout math: `core/layout.py` `compute_layout_positions` (grid/circle/line/scatter
  + deterministic, GPU-free jitter) — reusable building block for placement/level-building tools.
  8 tests. Next: wire a `unity_place_*` tool on top of it. — tests: 42 passed
- [cycle 3] P1 placement tool: `unity_place_primitives` — places N primitives in a chosen layout
  via the bridge, with a 500-object safety cap (also guards against scene-flooding). Builds on
  cycle 2's layout math. 3 tests. — tests: 45 passed
- [cycle 4] P1 structure math: `compute_structure_positions` (wall/tower/stairs/room/floor) —
  block-out building blocks for level design. 6 tests. Next: `unity_build_structure` tool. —
  tests: 51 passed
- [cycle 5] P1 structure tool: `unity_build_structure` — "build a wall/tower/stairs/room/floor"
  via the bridge using cycle-4 math, 500-block safety cap. 3 tests. — tests: 54 passed
- [cycle 6] P1 lighting math: `core/lighting.py` `compute_studio_lighting_rig` (3-point
  key/fill/rim) — toward presentable scenes. 4 tests. Next: `unity_setup_studio_lighting` tool. —
  tests: 58 passed
- [cycle 7] P1 lighting tool: `unity_setup_studio_lighting` — "set up studio lighting" creates a
  key/fill/rim rig via the bridge (create_light). 2 tests. — tests: 60 passed
- [cycle 8] P1 camera framing: `core/camera.py` `frame_camera_pose` + `unity_frame_camera` tool —
  orbit/frame a target for a presentable shot. Completes the P1 "presentable scene" set
  (place + build + light + frame). 6 tests. — tests: 66 passed
- [cycle 9] P2 color: `core/palette.py` `resolve_color` (name en+tr / hex / r,g,b) +
  `unity_set_object_color` — "make the cube red/kirmizi" instead of raw RGB. 6 tests. —
  tests: 72 passed
- [cycle 10] CAPSTONE: `unity_blockout_scene` — one command composes floor + scattered props +
  studio lighting + framed camera (uses cycles 2-8). "Empty scene -> composed scene" in one shot,
  with object caps. 4 tests. — tests: 76 passed
- [cycle 11] P4 robustness: `unity_save_scene` no longer always reports ok=true — it honors the
  editor's actual SaveScene result (a real "ok=true lie" from the audit). 3 tests. — tests: 79 passed
- [cycle 12] P2 themed color: `theme_palette` (fantasy/nature/warm/cool/mono) + `unity_color_group`
  — "color these props in a fantasy palette", cycling colors over a named group. 4 tests. —
  tests: 83 passed
- [cycle 13] P5 docs: `docs/GAME_STUDIO_TOOLS.md` — a catalog of the night's new autopilot tools
  with example en/tr commands (morning-review reference). docs-only. — tests: 83 passed

---

## — NIGHT COMPLETE (morning wrap-up) —

13 verified cycles landed on `autonomous/game-studio` (14 commits ahead of `main`), 83/83 tests
green, nothing left uncommitted. The autopilot grew from "creates one object at a time" into a
small game-studio toolkit: **placement** (`unity_place_primitives`), **blockout building**
(`unity_build_structure`), **3-point lighting** (`unity_setup_studio_lighting`), **camera framing**
(`unity_frame_camera`), **one-shot scene composition** (`unity_blockout_scene`), and **color/theme**
(`unity_set_object_color`, `unity_color_group`) — all natural-language (en/tr), all bridge-driven,
all backed by GPU-free, unit-tested math. Two reliability fixes from the original audit also landed:
the **repeated-tool-call guard** (no more "10 spheres for one request") and **honest `save_scene`**
(no more `ok=true` lies).

**Morning options:** review this log + the branch → if good, one PR merges the night's work into
`main`. Remaining backlog (P0 intent parsing, P3 memory read-back, P4 RPC/Anthropic robustness)
is in `GAME_STUDIO_ROADMAP.md` for the next run. Restart anytime with `/loop`.
