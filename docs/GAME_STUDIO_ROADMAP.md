# Autonomous Game-Studio Roadmap

**North star (aspirational):** an autopilot that can build a high-quality game from scratch —
creative scene/level design, materials/lighting, gameplay systems, asset pipeline, iteration &
learning. AAA is the *direction*, not an overnight deliverable. Each night = concrete, verified,
incremental capability gains.

**Working rules (every cycle):**
1. Work ONLY on branch `autonomous/game-studio`. Never touch `main`, never delete data, never
   commit secrets (`.env`, `*.pem`).
2. Pick the highest-priority unchecked item below (or a clear sub-step of it).
3. Implement a small, focused change. Keep cycles bounded.
4. **Verify:** `pytest` must pass and `python -c "import unitytools..."` must succeed. If a change
   breaks them and can't be fixed quickly, revert it.
5. Commit with a clear message, append a line to `docs/GAME_STUDIO_PROGRESS.md`, push the branch.
6. Schedule the next cycle.

## Backlog (priority order)

### P0 — Autopilot reliability (fix what we just saw)
- [x] **Stop over-creation / max-iterations.** (cycle 1) Added a repeated-tool-call guard in the
  ollama/cloudflare tool loops: if the model requests the same tool-call set twice in a row, stop
  with `stop_reason=repeated_tool_calls`. Verified: identical calls run once then stop; distinct
  calls still work. Follow-ups (b) prompt rule + (c) honor explicit counts remain.
- [ ] **Single vs batch intent.** Parse "bir/tek/one" vs "N tane/birçok/many" → set creation count;
  default to 1 when unspecified.
- [ ] **Completion detection.** After a successful mutating tool, prefer ending the turn unless the
  user asked for more.

### P1 — Level / scene building (toward "placement")
- [x] Layout math (cycle 2): `core/layout.py` `compute_layout_positions` — grid/circle/line/scatter
  + deterministic jitter, 8 tests. Tool wired (cycle 3): `unity_place_primitives`
  (grid/circle/line/scatter, 500-object safety cap, 3 tests).
- [x] Structure composition math (cycle 4): `compute_structure_positions`
  (wall/tower/stairs/room/floor), 6 tests. Tool wired (cycle 5): `unity_build_structure`
  (500-block safety cap, 3 tests).
- [x] Lighting preset math (cycle 6): `core/lighting.py` `compute_studio_lighting_rig` (3-point
  key/fill/rim), 4 tests. Tool wired (cycle 7): `unity_setup_studio_lighting` (2 tests).
- [x] Camera framing (cycle 8): `core/camera.py` `frame_camera_pose` + `unity_frame_camera` tool
  (orbit a target by distance/yaw/pitch, optional fov), 6 tests. **P1 "presentable scene" set now
  complete: place + build + light + frame.**
- [x] One-shot scene blockout (cycle 10): `unity_blockout_scene` composes floor + scattered props +
  studio lighting + framed camera into a single autopilot action (caps: 17x17 floor, 50 props).
  4 tests.

### P2 — Visual quality (toward "AAA look", pipeline-agnostic where possible)
- [x] Color tool (cycle 9): `core/palette.py` `resolve_color` (name en+tr / hex / r,g,b) +
  `unity_set_object_color`, 6 tests. Themed palettes (cycle 12): `theme_palette` +
  `unity_color_group` (fantasy/nature/warm/cool/mono), 4 tests. **Follow-up:** metallic/smoothness.
- [ ] Lighting rigs (key/fill/rim, ambient, fog) presets.
- [ ] Post-process / quality-tier helpers (guarded so they no-op without URP/HDRP).

### P3 — Learning & memory (toward "learning / focus")
- [ ] Make long-term memory actually READ BACK (cross-session learning is currently write-only).
- [ ] Feed recalled patterns/lessons into planning prompts.
- [ ] Game-studio kernel: tighten the evolution loop (metrics → weak points → next plan).

### P4 — Robustness (from the original audit)
- [ ] RPC request/response correlation after timeouts.
- [ ] Anthropic loop 400-lock on unanswered tool_use blocks.
- [x] Stop "ok=true" lies — `unity_save_scene` now honors EditorSceneManager's result instead of
  always returning ok=true (cycle 11, 3 tests). **Follow-up:** blender export + unreal import.
- [ ] Fix dual_agent mojibake (UTF-8 prompts).

### P5 — Tests & docs
- [ ] Unit tests for new tools + the P0 loop logic.
- [x] Game-studio tools catalog (cycle 13): `docs/GAME_STUDIO_TOOLS.md` — capability reference with
  example natural-language commands (en/tr).

> Check items off in this file as they land. Add new items as discovered.
