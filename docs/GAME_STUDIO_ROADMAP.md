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
  (Turkish "orman kur" → pattern section). Recall upgraded (cycle 12): `recall_similar` now scores
  by IDF-weighted Jaccard over Turkish-normalized, stopword-filtered tokens (was a raw overlap
  count) — length-normalized and rewards distinctive subject words over boilerplate; pure Python (no
  neural embeddings — GPU-free). 6 tests + live proof (a rare "dungeon" entry outranks 6 common
  "forest" ones).
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

- [x] Unity fast-action planner (cycle 6). `plan_unity_fast_action` mirrors the Unreal planner for
  the PRIMARY engine: Turkish/English intent → ordered `unity_*` steps with write flags + safety
  notes (forest/blockout/place/lighting/palette/find/delete/QA/quality/profile/catalog/record).
  `preflight_prompt` now routes Unity too; `gamestudio_plan_unity_fast_action` tool added. Token-
  prefix matching avoids substring false hits. 10 tests + live proof. Follow-up DONE (cycle 10):
  `run_unity_fast_action` (game_studio_actions) executes the planned steps against resolver-provided
  tools with event streaming — the LLM-free Unity counterpart of chat_server's Unreal fast-path —
  wired into chat_server as `_try_local_unity_action` (engine_context=="unity"). Tools resolve from
  the @tool registry (no hand-maintained map → drift-free). 5 tests + live proof (Turkish "sahneyi
  listele" ran unity_get_scene_catalog against the real editor, no LLM).

### P4 — Robustness (from the original audit)
- [ ] RPC request/response correlation after timeouts.
- [ ] Anthropic loop 400-lock on unanswered tool_use blocks.
- [x] Stop "ok=true" lies — `unity_save_scene` now honors EditorSceneManager's result instead of
  always returning ok=true (cycle 11, 3 tests). **Follow-up:** blender export + unreal import.
- [x] Fix dual_agent mojibake (cycle 8). The Master/Reader/Worker prompts were valid UTF-8 whose
  *characters* were the double-encoded mojibake string ("KullanÄ±cÄ±" instead of "Kullanıcı", 594
  markers) — wasting tokens + degrading Turkish comprehension every planning call. Reverse-decoded
  (mixed latin-1/cp1252), restored 2 lost "ç" in "ağaç", dropped the UTF-8 BOM (which made readers
  misrender it). `tests/test_encoding.py` guards it. (Investigation note: terminal/Read-tool
  rendering initially made it look clean — codepoint inspection (0xc4 0xb1 vs 0x131) settled it.)
  Also fixed (cycle 11): `dual_chat.py`'s 3 mojibake'd emoji CLI labels (🧠 Master / 🔧 Tool /
  📊 Result) — restored via precise escape-based replacement (the global demoji was lossy here),
  BOM dropped, guarded by `tests/test_encoding.py`.
- [x] Dead-code cleanup (cycle 7): removed orphan `simple_dual_agent.py` (+ its root test), the unused
  `TaskQueue`/`task_queue.py` export, and the stale `protocol.UNITY_METHODS` (phantom
  `run_csharp_script`). grep-verified dead, +5 regression-guard tests, 180 green. `safe_contained_path`
  wired (cycle 13): `unity_restore_scene_snapshot` confines the model-chosen path to `Assets/` and
  rejects absolute / drive-letter / `..`-escaping paths before the bridge opens it (legit
  Assets/AutopilotSnapshots/*.unity still pass). `import_asset` intentionally untouched (takes an
  external source path by design). +13 tests (incl. safe_contained_path itself, untested before).

### P5 — Tests & docs
- [x] Unit tests for new tools + the P0 loop logic. (cycles 1-13 + day-1 wired tools = 122 tests)
- [x] Game-studio tools catalog (cycle 13): `docs/GAME_STUDIO_TOOLS.md` — capability reference with
  example natural-language commands (en/tr).
- [x] Tool-registry collision guard + de-dup (cycle 3). `tool_registry` now warns and tracks
  duplicate @tool registrations (`get_collisions()`). The 15 day-1 tools turned out to duplicate
  pre-existing `scene_intelligence_tools`/`autopilot_quality_tools` versions (the day-1 audit only
  grepped `unity_tools.py`); consolidated onto the tested+live-proven `unity_tools` copies —
  collisions **15 → 0**, guarded by `tests/test_no_tool_collisions.py`. Follow-up DONE (cycle 9):
  ported the removed copies' explicit per-call timeouts (60–240s) onto all 15 `unity_tools` wrappers
  so slow ops (texture repair 240s, LOD 240s) don't hit the 180s default. (`is_connected()` port
  unnecessary — `UnityBridge.call` already raises if disconnected.)

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

### P7 — Gameplay authoring (scene decorator → game maker, the biggest gap)
The studio can place/decorate but not yet author gameplay. This is the road to "builds a game".
- [x] Physics behaviours via existing tools (cycle 15): `core/gameplay.py` catalog +
  `unity_add_gameplay_behaviour` compose Rigidbody/collider into real physics primitives
  (physics/falling/heavy/floaty/kinematic/static_obstacle). Live-proven (a cube became a
  physics-driven object). Script-only behaviours flagged `needs_script`.
- [~] Scripted behaviours (rotator/mover). Cycle 17 STEP A (done): `core/gameplay.generate_behaviour_script`
  produces deterministic, balanced-brace C# MonoBehaviour source (AutopilotRotator/Mover, parametric
  axis+speed); `unity_add_script_behaviour` tool returns it, and with `auto_import=True` writes+imports
  it via the EXISTING `import_asset` (no new C# command needed — supersedes the originally-planned C#
  handler). `needs_script` planner responses now carry the generated source. 8 tests, source shown
  live. End-to-end flow DONE (cycle 18): `unity_apply_script_behaviour` chains generate → import →
  `wait_until_compiled` (bounded poll of get_editor_state) → `add_component`. The poll is a pure
  injectable helper (unit-tested: compiles-after-N, timeout, error-tolerance); ordering verified with
  a fake bridge. The one unverified bit is the live recompile run — importing a .cs reloads the Unity
  domain (briefly drops the bridge), risky to trigger unattended, so run it with the editor in focus;
  the safe poll source (get_editor_state) was confirmed live.
- [x] Idempotent collider (cycle 16): `prune_redundant_steps` + `unity_add_gameplay_behaviour` now
  query the object's components and skip adding a collider when one already exists (Cube/Sphere
  primitives ship one). Live-proven (re-applying physics skips the collider). 6 tests.
- [x] Player controller / input primitive (cycle 19): `AutopilotPlayerController` MonoBehaviour
  template — WASD via Input.GetAxis + Space jump with gravity/ground handling, parametric moveSpeed.
  Mapped player/controller/oyuncu/karakter/pawn. 5 tests, source shown live (compilable, balanced).
- [x] Win/lose trigger zones (cycle 20): `AutopilotCollectible` / `AutopilotGoalZone` /
  `AutopilotKillZone` OnTriggerEnter MonoBehaviours (pickup-destroy / win-flag / respawn). Each
  `Reset()` auto-sets `collider.isTrigger=true` + `[RequireComponent(Collider)]`, so triggers work
  with no manual setup. en+tr aliases (toplanabilir/coin, hedef/win, olum/lava). 13 tests.
- [x] **Playable game skeleton (cycle 21)** — `core/game_blueprint.plan_collectathon_game` composes
  the building blocks into a full ordered plan (ground + tagged WASD player + N collectibles + goal);
  `unity_build_simple_game` returns it (execute=False, safe) or builds it (execute=True, recompiles).
  6 tests; live proof: a 12-step collect-a-thon plan for "build me a simple collect game". **The
  first end-to-end self-makes-a-game capability** — the culmination of the cycle 15-21 gameplay arc.
- [x] Execute-path optimization (cycle 22): `group_execution_plan` splits a blueprint into
  geometry / distinct scripts / attachments; `unity_build_simple_game` execute now imports each
  unique behaviour script ONCE (one recompile phase) then attaches to every target — a 5-collectible
  game drops from 7 script imports to 3. 2 tests (incl. import-count assertion).
- [~] More blueprints. Dodge added (cycle 23): `plan_dodge_game` — ground + WASD player + N MOVING
  hazards (mover + killzone composed) + goal; `unity_build_simple_game(game_type='dodge')`. Proves the
  blueprint pattern generalizes (same blocks → a different game). 6 tests. Spawner/wave added (cycle
  24): `AutopilotSpawner` MonoBehaviour — InvokeRepeating spawns physics cubes at a parametric
  interval up to maxCount (with CancelInvoke), aliases spawn/wave/dalga. 6 tests.
- [x] **Blueprint catalog + "build me a game" intent (cycle 25)** — `BLUEPRINTS` registry +
  `plan_game(game_type, count)` dispatcher; `plan_unity_fast_action` routes natural-language game
  requests ("bana bir dodge oyunu kur", "toplama oyunu yap", "build me a game") to
  `unity_build_simple_game` (execute=False, safe). 6 tests; live-proven. **Closes the intent→game
  loop:** a Turkish/English request → the full plan for that game. Survival added (cycle 26):
  `plan_survival_game` — ground + WASD player + M elevated hazard spawners; routed by intent (sağ
  kalma / survive). Catalog now has 3 games (collectathon, dodge, survival). 6 tests.
- [x] Games doc (cycle 27): `docs/GAME_STUDIO_GAMES.md` — game-type table, behaviour catalog
  (physics + scripted), intent phrases (tr/en), execute/recompile notes, and a "add a blueprint"
  guide. Guarded by `tests/test_games_doc.py` (every referenced tool/behaviour/game verified against
  the live registry — no phantoms; caught the "declared-but-not-templated" set too). Linked from
  GAME_STUDIO_TOOLS.md. **Remaining:** platformer blueprint, in-game score/HUD.

> Check items off in this file as they land. Add new items as discovered.
