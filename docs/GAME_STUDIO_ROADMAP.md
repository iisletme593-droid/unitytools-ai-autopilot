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
- [x] Make long-term memory actually READ BACK (cycle 1, post-scan). `MemorySystem._load_long_term`
  loads `long_term_memory.jsonl` at init (capped to the most recent 500); `recall_similar`/
  `get_lessons` now search prior sessions too. Was write-only before → the core "learns across
  sessions" goal now functions. 6 tests + live write→restart→recall proof.
- [x] Feed recalled patterns/lessons into planning prompts (cycle 2). `format_pattern_section`
  injects the learned Pattern (success rate, best-approach tools, pitfalls) into the master prompt;
  `get_pattern` unified with `_classify_request` and both extended with Turkish keywords so patterns
  actually resolve for the (Turkish-driven) autopilot. Was dead-ended before. 5 tests + live proof
  (Turkish "orman kur" → pattern section). **Follow-up:** embedding-based recall (still keyword).
- [x] Auto-record experiments with MEASURED metrics (cycle 5). `core/quality.metrics_from_signals`
  derives clarity_score (structural cleanliness) + an fps proxy (triangle budget) + crash_count from
  visual-QA & profiling; `gamestudio_record_scene_experiment` runs QA+profile on the live scene and
  auto-writes a kernel experiment. Closes measure→record→recall→plan (no more always-None hand-typed
  metrics). 7 tests + live proof (recorded a "promising" experiment from the real editor scene).
- [~] Game-studio kernel: tighten the evolution loop (metrics → weak points → next plan).
  First concrete loop landed (day 1): `unity_quality_pass` runs an in-scene metrics→weak-points→fix
  cycle via `core/quality.assess_qa`. Weak-point ranking fixed (cycle 4): `_infer_weak_points` now
  normalizes each metric to a 0–1 goodness (`_metric_goodness`) before ranking, so a bad fps (35/60)
  outranks a good fun (7/10) — it used to be driven by raw magnitude. Still open: persist verdicts
  across sessions and feed them into planning (depends on the memory-read-back items above).

### P4 — Robustness (from the original audit)
- [ ] RPC request/response correlation after timeouts.
- [ ] Anthropic loop 400-lock on unanswered tool_use blocks.
- [x] Stop "ok=true" lies — `unity_save_scene` now honors EditorSceneManager's result instead of
  always returning ok=true (cycle 11, 3 tests). **Follow-up:** blender export + unreal import.
- [ ] Fix dual_agent mojibake (UTF-8 prompts).

### P5 — Tests & docs
- [x] Unit tests for new tools + the P0 loop logic. (cycles 1-13 + day-1 wired tools = 122 tests)
- [x] Game-studio tools catalog (cycle 13): `docs/GAME_STUDIO_TOOLS.md` — capability reference with
  example natural-language commands (en/tr).
- [x] Tool-registry collision guard + de-dup (cycle 3). `tool_registry` now warns and tracks
  duplicate @tool registrations (`get_collisions()`). The 15 day-1 tools turned out to duplicate
  pre-existing `scene_intelligence_tools`/`autopilot_quality_tools` versions (the day-1 audit only
  grepped `unity_tools.py`); consolidated onto the tested+live-proven `unity_tools` copies —
  collisions **15 → 0**, guarded by `tests/test_no_tool_collisions.py`. **Follow-up:** port the
  removed copies' richer per-call timeouts (60–240s) and `is_connected()` check onto the
  `unity_tools` versions.

### P6 — Expose the bridge's existing power (the real gap, found on review)
The C# bridge already implements far more than the Python tool layer exposes. Wrapping an existing
command is higher-leverage than reinventing a weaker version of it. The active bridge has 65
commands; audit which still lack a `unity_*` tool and wire the high-value ones.
- [x] Wire 15 unexposed bridge commands as `@tool`s (day 1): material palette/diagnose/repair,
  texture-import repair, optimized forest scene, scene catalog, semantic find/delete, visual QA,
  scene snapshot/restore, performance profile, editor optimize, LOD analyze/apply. Params grounded
  in the real C# handlers, +39 tests, registry test included. **This also fixed the system prompt
  referencing `unity_apply_material_palette` / `unity_create_optimized_forest_scene` before those
  tools existed.**
- [x] Audit the remaining unexposed commands (day 1). **Finding:** the *active* plugin bridge has
  exactly **49 real commands** (the earlier "65" was inflated by a `SynonymsFor` switch — those
  `forest/village/terrain/...` tokens are synonym keywords, not commands). After the 15 wired tools,
  **all 49 active commands are now exposed**, and an inverse audit confirmed **no tool calls a
  non-existent bridge command**. The richer terrain/particles/UI/atmosphere/behaviour commands live
  only in the larger *worktree* bridge, not the installed plugin — wrapping them would create
  phantom tools, so that work is gated on expanding (or merging in) the active C# bridge first.
- [x] Wire `unity_run_visual_qa` into an actual iterate loop (day 1): `core/quality.py` `assess_qa`
  (pure: QA verdict → pass/score/fix-actions) + `unity_quality_pass` tool (build → QA → fix →
  re-check, snapshots before fixing, bounded passes). This is the mechanical half of P3
  "learning/focus". 9 tests.
- [x] Snapshot-before-mutate (day 1): `core/safety.py` (`DESTRUCTIVE_TOOLS`, `is_destructive`,
  `snapshot_label_for`) + an orchestrator hook in the single `_execute_tool` path that auto-saves a
  scene snapshot before the first destructive tool of each turn (best-effort, once per turn). 7
  tests.

> Check items off in this file as they land. Add new items as discovered.
