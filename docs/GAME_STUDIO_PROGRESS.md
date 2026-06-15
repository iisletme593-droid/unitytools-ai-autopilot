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

---

## — DAY 1: expose the bridge's existing power (post-review) —

**User review caught a real problem:** most of the night's "new" tools were thin re-wraps of
things the LLM could already approximate from primitives. The genuinely-new value was only the 2
reliability fixes. The deeper issue surfaced on inspection: the C# bridge (`CommandHandlers.cs`)
exposes **65 commands**, but the Python tool layer only wrapped ~42 of them — so the autopilot's
LLM physically could not reach material palettes, semantic find/delete, scene catalog, optimized
forest generation, visual QA, snapshots, or performance/LOD tooling. Worse, the orchestrator system
prompt *instructed* the LLM to call `unity_apply_material_palette` and
`unity_create_optimized_forest_scene` — tools that did not exist.

- [day1] **Wired 15 existing bridge commands into Python @tool wrappers** (params grounded in the
  real C# handlers, verified line-by-line): `unity_apply_material_palette`,
  `unity_diagnose_material_issues`, `unity_repair_material_issues`,
  `unity_repair_texture_import_settings`, `unity_create_optimized_forest_scene`,
  `unity_get_scene_catalog`, `unity_find_scene_objects_semantic`,
  `unity_delete_scene_objects_semantic`, `unity_run_visual_qa`, `unity_create_scene_snapshot`,
  `unity_restore_scene_snapshot`, `unity_profile_scene_performance`,
  `unity_optimize_editor_performance`, `unity_analyze_lod_decimation_candidates`,
  `unity_apply_lod_decimation_plan`. Built via a 5-agent workflow that read the C# and generated
  matching code+tests; integrated, deduped into one test file, and verified. +39 tests
  (incl. a registry test proving all 15 are exposed to the LLM). The two tools the system prompt
  already referenced now actually exist — the prompt no longer promises phantom tools. —
  tests: 122 passed
- [day1] **P6 completed.** (a) **Audit finding:** the active plugin bridge has 49 real commands (the
  "65" was synonym-switch noise), and after the 15 wraps **every active command is exposed** with
  **no phantom tool→bridge calls** (inverse audit). Richer terrain/particle/UI/behaviour commands
  exist only in the worktree bridge, so they're gated on expanding the active C# first. (b)
  **Quality loop** (`core/quality.py` + `unity_quality_pass`): build → `run_visual_qa` → assess →
  auto-fix broken/missing materials & missing lights → re-check, snapshotting before any fix; pure
  assessment is unit-tested. (c) **Snapshot safety** (`core/safety.py` + orchestrator `_execute_tool`
  hook): auto-saves a scene snapshot before the first destructive tool of each turn (once per turn,
  best-effort). +16 tests. — tests: 138 passed
- [day1] **LIVE VERIFIED against the running Unity Editor** (port 7779, token auth). `scripts/
  live_check.py`: connect → ping → scene catalog (SampleScene, 14 objs) → `unity_create_scene_snapshot`
  (wrote a real .unity under Assets/AutopilotSnapshots) → `unity_run_visual_qa` (captured a
  screenshot, "Scene QA passed.") → `unity_quality_pass` (score 100). `scripts/forest_demo.py`:
  one command `unity_create_optimized_forest_scene` built a 48-object optimized forest (terrain +
  40 trees + rocks, editor quality auto-lowered for the GPU-less machine), then QA passed (145 objs,
  101 renderers, 0 broken materials). The wired tools + quality loop + snapshot all work on the real
  editor. (Auto-fix branch stays test-only — both live scenes were already clean.)

---

## — AUTONOMOUS STUDIO LOOP (post full-scan, ~25 min cadence) —

An 8-agent `game-studio-full-scan` mapped every subsystem against the "fully autonomous,
self-learning game studio" goal. Top cross-cutting findings: (1) cross-session learning was BROKEN
(write-only memory), (2) learned patterns are computed but never used in planning, (3) ~15 tools are
shadowed dead duplicates, (4) `_infer_weak_points` misranks (unnormalized), (5) experiments aren't
auto-recorded, (6) the studio loop is Unreal-only, (7) dead code (TaskQueue, simple_dual_agent,
phantom `protocol.UNITY_METHODS`/`run_csharp_script`, unwired `safe_contained_path`). Plan: one
focused, tested, live-proven, deployed improvement per ~25-min cycle.

- [cycle 1] P3 cross-session learning FIXED: `MemorySystem._load_long_term` loads
  `long_term_memory.jsonl` at init (recent-500 cap, malformed-line tolerant); `recall_similar`/
  `get_lessons` now search prior sessions (deduped session+disk). Was write-only → "learns across
  sessions" now works. +6 tests; live proof: write → fresh instance (restart) → recalled the prior
  request. — tests: 144 passed
- [cycle 2] P3 learned-pattern injection: `dual_agent.format_pattern_section` puts the learned
  Pattern (success rate, best-approach tools, common pitfalls) into the master planner prompt — it
  was computed (`get_pattern`) and persisted but never used. Also unified `get_pattern` with
  `_classify_request` and added Turkish keywords to both, so patterns actually resolve for the
  Turkish-driven autopilot (was English-only). +5 tests; live proof: Turkish "orman kur" → learned
  pattern section with best tools. — tests: 149 passed
- [cycle 3] Tool de-dup + registry collision guard. The scan found ~15 shadowed dead tools; turned
  out they were the day-1 wired tools duplicating PRE-EXISTING `scene_intelligence_tools` (9) and
  `autopilot_quality_tools` (6) versions (the day-1 audit only grepped unity_tools.py — honest
  miss). Kept the tested+live-proven `unity_tools` copies; rewrote `scene_intelligence_tools.py`
  (deleted 9 dups, kept the unique knowledge-base export) and de-registered the 6 autopilot dups
  (kept undecorated because `unity_create_lod_decimation_plan` calls them internally). Added a
  collision warning + `get_collisions()` to `tool_registry`. Collisions 15→0. +3 tests; live
  regression check against the editor still green. — tests: 152 passed
- [cycle 4] Kernel weak-point ranking fixed: `_infer_weak_points` summed raw metrics, so
  fps_average (~90) never ranked weak and a good fun_score (~7) was wrongly flagged. Now each metric
  is normalized to a 0–1 goodness (`_metric_goodness`, fps ceiling 60, scores ceiling 10) and
  averaged per-metric before ranking ascending. Iteration focus now follows quality, not scale.
  +6 tests; live proof: fun=9/clarity=8/fps=30 → fps correctly flagged weakest. — tests: 158 passed
- [cycle 5] Closed the build→measure→learn loop. `core/quality.metrics_from_signals` turns
  `unity_run_visual_qa` + `unity_profile_scene_performance` output into measured metrics
  (clarity_score, fps proxy from triangle budget, crash_count; fun/difficulty left None as not
  measurable). New tool `gamestudio_record_scene_experiment` runs QA+profile on the live scene and
  auto-records a kernel experiment — no more always-None hand-typed metrics. Combined with cycles
  1/2/4, the studio now measures→records→recalls→ranks. +7 tests; live proof: recorded a "promising"
  experiment (clarity 10, fps proxy 60) from the real editor forest scene. — tests: 165 passed
- [cycle 6] Unity fast-action planner (the studio loop now runs on the PRIMARY engine). The
  self-evolving planner was Unreal-only; added `plan_unity_fast_action` (+ wired `preflight_prompt`
  for Unity + `gamestudio_plan_unity_fast_action` tool) mapping Turkish/English intents to the
  existing unity_* tools — forest/blockout/place/lighting/palette/find/delete/QA/quality-pass/
  profile/catalog/record-experiment — with write flags + safety notes for destructive steps.
  Token-prefix matching (not anywhere-substring) avoids false hits like "naSİLsin"→delete. +10 tests
  (incl. a guard that every emitted tool is registered); live proof: compound Turkish prompt →
  ordered snapshot→forest→quality-pass plan. — tests: 175 passed
  (NOTE: the ~25-min auto-wakeup loop stalled ~6.5h between cycle 5 and 6 because ScheduleWakeup is
  session-local and pauses when the machine sleeps; work is committed each cycle so nothing was lost,
  resumed on the next message.)
- [cycle 7] Dead-code cleanup (grep-verified unused, then test-confirmed). Removed: `simple_dual_agent.py`
  (orphan, no importers) + its broken root orphan test `test_simple_dual.py`; the `TaskQueue`/`Task`/
  `TaskStatus` export from `core/__init__.py` and the unused `core/task_queue.py` (the live "task
  queue" is a separate JSON-file tool in autopilot_quality_tools); and the stale
  `protocol.UNITY_METHODS` set (unused, advertised a phantom `run_csharp_script`, omitted ~40 real
  commands). +5 regression-guard tests; import + 180 tests green; live editor check still green.
  Deferred: wiring `safe_contained_path` (a behavior-adding security change — import_asset takes
  external source paths, needs care). — tests: 180 passed
- [cycle 8] Fixed dual_agent.py mojibake. The Master/Reader/Worker Turkish prompts were stored as
  valid UTF-8 whose characters were the double-encoded mojibake (0xC4 0xB1 "Ä±" instead of 0x131
  "ı"; 594 markers) — wasting tokens + hurting comprehension on every Master/Reader call. Reverse-
  decoded with a mixed latin-1/cp1252 pass, restored 2 lost "ç" (in "ağaç"), and dropped the UTF-8
  BOM that made tools misrender the file. +3 encoding-guard tests; codepoint-verified clean (Kullan
  → 0x131). Honest note: terminal/Read-tool rendering first made it *look* already-correct — only a
  raw codepoint check (0xc4 0xb1 vs 0x131) exposed the real corruption. — tests: 183 passed
- [cycle 9] Ported explicit per-call timeouts onto the 15 wired `unity_tools` wrappers (cycle-3
  follow-up): get_scene_catalog/find_semantic 60, delete_semantic/diagnose 90, apply_palette/QA/
  profile/analyze_lod 120, repair_materials/forest 180, repair_texture/apply_lod 240, snapshot/
  restore/optimize 60. Slow ops (texture repair, LOD) previously hit the 180s default and could
  time out. Updated 3 test fakes' `call()` to accept `timeout=`. (is_connected port skipped —
  `UnityBridge.call` already raises when disconnected.) 183 tests green; live editor check green
  (timeout'd snapshot/QA/catalog calls succeeded). — tests: 183 passed
- [cycle 10] LLM-free Unity fast-action executor. `run_unity_fast_action` (game_studio_actions) takes
  a prompt → plan_unity_fast_action → runs each step against resolver-provided tools with event
  streaming; returns None when there's no plan (caller falls through to the LLM). Wired into
  chat_server as `_try_local_unity_action` (engine_context=="unity"), resolving tools from the @tool
  registry (no hand-maintained tool_map like the Unreal path → drift-free). Deterministic logic lives
  in a separately-testable function. +5 tests; live proof: Turkish "sahneyi listele" planned +
  executed unity_get_scene_catalog against the real editor (145 objects), streaming
  thinking→tool_call→tool_result, no LLM. — tests: 188 passed
- [cycle 11] Fixed dual_chat.py emoji mojibake. 3 CLI status labels were double-encoded emoji
  ("ğŸ§ Master" etc.). Unlike dual_agent.py, the global demoji was lossy here (9 FFFD), so used a
  precise escape-based replacement: 🧠 Master / 🔧 Tool / 📊 Result restored to real codepoints
  (0x1f9e0/0x1f527/0x1f4ca), BOM dropped. Cosmetic (CLI only, not model-facing). +1 guard test in
  test_encoding.py. — tests: 189 passed
- [cycle 12] Smarter memory recall. `MemorySystem.recall_similar` replaced the raw keyword-overlap
  count with an IDF-weighted Jaccard over Turkish-normalized (`ağaç`→`agac`), stopword-filtered
  tokens: length-normalized and rewards sharing distinctive subject words (`dungeon`) over the
  boilerplate verbs/articles every request shares. Pure Python, GPU-free; backward compatible
  (cross-session recall tests still pass). +6 tests; live proof: with 6 "orman" entries + 1 "zindan",
  the query "orman zindan" ranks the rare zindan entry first (raw overlap would tie them). —
  tests: 195 passed
- [cycle 13] Security: wired the dead `safe_contained_path` into `unity_restore_scene_snapshot`. The
  model picks the restore path, so it's now confined to `Assets/` with absolute / drive-letter /
  `..`-escaping paths rejected before the bridge opens the scene; legit Assets/AutopilotSnapshots
  paths still pass. `import_asset` left untouched (external source paths by design). +13 tests (incl.
  safe_contained_path itself, untested before); live proof: malicious path rejected (bridge not
  called), legit path forwarded. — tests: 208 passed
- [cycle 14] Context: props/characters/weapons asset-finders now feed ContextManager.
  `_update_context_from_tools` only wired tree/rock, so prop/character context stayed empty though
  `update_assets` already supported them. Refactored the tree/rock elif chain into a
  `ASSET_FINDER_CATEGORIES` mapping (+ prop/character/weapon→props). +5 tests (lightweight: unbound
  method + fake self, no orchestrator build); live proof: prop+character finders populate
  context.assets. — tests: 213 passed
- [cycle 15] **GAMEPLAY AUTHORING begins** — the biggest capability gap (scene decorator → game
  maker). The C# `add_component` adds built-in/project components but sets no properties; `set_rigidbody`
  both adds AND configures a Rigidbody. So `core/gameplay.py` (behaviour catalog) + the new
  `unity_add_gameplay_behaviour` tool compose existing Rigidbody/collider tools into real physics
  primitives (physics/falling/heavy/floaty/kinematic/static_obstacle, en+tr aliases) — no new C#
  needed. Script-only behaviours (rotate/patrol/follow) are honestly reported as `needs_script`
  (a future `add_script_behaviour` bridge command), not faked. +10 tests; **LIVE PROOF: a test cube
  was given "physics" and now carries Rigidbody + Collider — a static prop became a physics-driven
  game object in the real editor.** Follow-up: idempotent collider (primitives already have one);
  C# add_script_behaviour for scripted movement. — tests: 223 passed
- [cycle 16] Idempotent collider. `core/gameplay.prune_redundant_steps` + `unity_add_gameplay_behaviour`
  now read the object's components (get_object_details) and skip the add-collider step when one is
  already present, so re-applying "physics" no longer stacks colliders (Cube primitives ship one).
  +6 tests; live proof: re-applying physics to the cycle-15 test cube skipped add_collider. (C#
  add_script_behaviour for scripted movement deferred to its own cycle — compile risk.) — tests: 227 passed
- [cycle 17] Scripted-behaviour authoring (STEP A, safe). `core/gameplay.generate_behaviour_script`
  emits deterministic, balanced-brace C# MonoBehaviour source for rotate/spin/move
  (AutopilotRotator/Mover, parametric axis+speed); `unity_add_script_behaviour` tool returns it and,
  with opt-in auto_import, writes+imports it via the EXISTING `import_asset` — so no new (compile-risky)
  C# bridge command is needed. `needs_script` planner responses now carry the generated source. +8
  tests; live proof: a valid AutopilotRotator script generated (speed 120, balanced braces, correct
  Unity API). Default generate-only path triggers no Unity recompile (safe unattended). Cycle 18:
  end-to-end live import→recompile→add_component orchestration. — tests: 235 passed
- [cycle 18] Scripted-behaviour end-to-end flow. `unity_apply_script_behaviour` chains generate →
  import (auto_import) → `wait_until_compiled` (bounded poll of get_editor_state until is_compiling is
  False) → `unity_add_component`. The recompile-wait is a pure injectable helper (`core/gameplay`),
  fully unit-tested (compiles-after-N polls, timeout, get_state error tolerance); the tool's
  import→wait→attach ordering is verified with a fake bridge. +6 tests. Live: the poll source
  (get_editor_state) was confirmed readable live, but the actual recompile-triggering run was NOT
  done unattended — importing a .cs reloads the Unity domain and briefly drops the bridge, which
  could disrupt later autonomous cycles; it should be run with the editor in focus. (Discovered + fixed
  a test-fake bug: get_editor_state is called with no params, so fakes need params=None like the real
  bridge.) — tests: 241 passed
- [cycle 19] Player controller / input primitive. `AutopilotPlayerController` template added to the
  script catalog: WASD movement via `Input.GetAxis(Horizontal/Vertical)` + Space jump (manual gravity
  + ground clamp), parametric moveSpeed. Mapped player/controller + Turkish oyuncu/kontrolcu/karakter/
  pawn; flows through the existing unity_add_script_behaviour/unity_apply_script_behaviour. +5 tests;
  live proof: a compilable AutopilotPlayerController generated (Input.GetAxis, moveSpeed 6, balanced
  braces). The input/player layer of an actual game. — tests: 246 passed
- [cycle 20] Win/lose trigger zones — the game-logic layer. Added `AutopilotCollectible` (pickup →
  Destroy), `AutopilotGoalZone` (player enters → win flag), `AutopilotKillZone` (player enters →
  respawn) OnTriggerEnter MonoBehaviours. Each `Reset()` auto-sets `collider.isTrigger=true` and
  `[RequireComponent(Collider)]`, so the trigger works without manual editor setup. en+tr aliases
  (toplanabilir/coin/pickup, hedef/win/finish, olum/lava/hazard/tuzak). +13 tests; live proof:
  AutopilotCollectible source (OnTriggerEnter, CompareTag Player, Destroy, auto-isTrigger). With
  physics + scripted movement + player controller + these triggers, the full gameplay building-block
  set is in place. Cycle 21: assemble a playable game skeleton. — tests: 259 passed
- [cycle 21] **MILESTONE — playable game skeleton.** `core/game_blueprint.plan_collectathon_game`
  composes the building blocks into a complete ordered plan: ground → tagged WASD player → N
  collectibles (each a pickup) → goal zone. `unity_build_simple_game` returns the plan (execute=False,
  safe — no scene changes) or builds it (execute=True: geometry + script imports, triggers
  recompiles). +6 tests; live proof: a 12-step collect-a-thon plan generated for "build me a simple
  collect game". This is the first end-to-end "self-makes-a-game" capability — the culmination of the
  cycle 15–21 gameplay arc (physics → scripted movement → player controller → triggers → full game).
  In 21 cycles the studio went from "places trees" to "plans a playable game", all tested + deployed.
  — tests: 265 passed
- [cycle 22] Execute-path optimization (makes live game-build practical). `group_execution_plan`
  (pure) splits a blueprint into geometry / distinct script behaviours / attachments;
  `unity_build_simple_game` execute now imports each UNIQUE behaviour script once (→ one recompile
  phase) then attaches the compiled component to every target — so a 5-collectible game drops from 7
  script imports to 3 (player/collectible/goal), with the 5 collectibles sharing a single import. +2
  tests; live proof: grouped plan shows 3 unique scripts for a 5-collectible game. — tests: 267 passed
- [cycle 23] Second game blueprint — DODGE. `plan_dodge_game` composes the same building blocks into
  a different game: ground + WASD player + N MOVING hazards (each = mover + killzone) + goal;
  `unity_build_simple_game` gained a `game_type` param (collectathon default, dodge). group_execution_plan
  handles the 2-behaviour-per-object hazards generically (4 unique scripts: player/mover/killzone/goal).
  +6 tests; live proof: a 15-step dodge plan for 4 moving hazards. Proves the blueprint pattern isn't
  tied to one game — the autopilot can plan different games from the same parts. — tests: 273 passed
- [cycle 24] Spawner / wave behaviour. `AutopilotSpawner` MonoBehaviour template: `InvokeRepeating`
  spawns physics cubes at a parametric `interval` up to `maxCount` (then `CancelInvoke`), placed at
  the spawner's position. Mapped spawner/spawn/wave/dalga/uretici. The basis for waves / endless
  generation (and a future survival blueprint). +6 tests; live proof: AutopilotSpawner source
  (InvokeRepeating, CreatePrimitive, maxCount cap, balanced braces). — tests: 279 passed
- [cycle 25] **Blueprint catalog + "build me a game" intent — closes the intent→game loop.**
  `core/game_blueprint.BLUEPRINTS` registry (game_type→planner) + `plan_game`/`list_blueprints`
  dispatcher; `unity_build_simple_game` refactored onto it (backward compatible). Added a top-priority
  build-game intent to `plan_unity_fast_action`: "oyun kur/yap", "toplama oyunu", "dodge/kaçma oyunu",
  "build me a game" → a `unity_build_simple_game` step (execute=False, write=False — safe plan;
  game_type inferred). Ordered first so "oyun" doesn't fall into scene branches; non-game prompts
  (orman kur, sahneyi listele) unaffected. +6 tests; live proof: "bana bir dodge oyunu kur" → dodge,
  "toplama oyunu yap 7..." → collectathon/7. In 25 cycles: from "places trees" to "understands
  'build me a dodge game' and plans it end-to-end". — tests: 285 passed
- [cycle 26] Survival blueprint — a 3rd game type built on the spawner. `plan_survival_game`: ground
  + WASD player + M elevated hazard spawners (raining physics cubes); registered in BLUEPRINTS;
  build-game intent extended with survival/survive/sağ kalma/hayatta kal → game_type=survival. +6
  tests; live proof: survival plan (2 unique scripts: player/spawner) + "sağ kalma oyunu kur" →
  survival. Catalog now offers 3 games (collectathon, dodge, survival), all reachable by NL request.
  — tests: 291 passed
- [cycle 27] Games documentation. `docs/GAME_STUDIO_GAMES.md`: game-type table (collectathon/dodge/
  survival with example tr+en commands), the physics + scripted behaviour catalog, "build me a game"
  intent phrases, execute=False/True + recompile notes, and a guide for adding a blueprint. Built
  from verified catalog data and guarded by `tests/test_games_doc.py`, which scans the doc and asserts
  every `unity_*` tool / game type / behaviour actually exists (no phantom references — it caught a
  regex false-positive and the doc honestly lists the 7 declared-but-not-yet-templated behaviours).
  Linked from GAME_STUDIO_TOOLS.md. +4 tests. — tests: 295 passed
- [cycle 28] Platformer blueprint — the 4th game type. `core/game_blueprint.plan_platformer_game`:
  ground + a WASD player who already has a Space-to-jump controller + N cubes arranged as a climbing
  staircase (each platform a strict step higher and further: y=1.0,2.5,4.0,… z=3,6,9,…), each made a
  solid ledge with the `static_obstacle` physics behaviour (a plain tool step → no recompile), and a
  goal sitting on top of the highest platform that you can only reach by jumping up. Registered in
  `BLUEPRINTS` and dispatched by `plan_game`; only `player`+`goal` are scripted so the build is a
  single recompile (platforms are physics). `plan_unity_fast_action` routes "platform/zıplama oyunu",
  "platformer", "jump game" → game_type=platformer (other game intents unchanged). Added a row to
  `GAME_STUDIO_GAMES.md` §1 + intent phrases (still passes the no-phantom doc guard). +8 tests
  (structure, staircase-monotonicity, goal-above-top, count-clamp, grouping, intent routing).
  Live-proved the plan + 4 intent phrases (pure, execute=False). — tests: 303 passed
- [cycle 29] In-game score / HUD. New scripted behaviour `score` → `AutopilotScore` MonoBehaviour: a
  global `static int Score` (reset in Awake), a top-left `OnGUI` HUD ("Score: N"), and TWO ways to add
  points — the `static AutopilotScore.Add(n)` helper for direct callers and an instance `AddScore(n)`
  for `SendMessage`. The collectible (`AutopilotCollectible`) now increments on pickup via
  `other.SendMessage("AddScore", 1, SendMessageOptions.DontRequireReceiver)` — it messages whoever
  picked it up (the Player) with NO reference to the AutopilotScore type, so the collectible stays
  self-contained and compiles with or without a HUD ("(varsa)" by construction). The collectathon
  blueprint attaches `score` to the Player (one persistent object, no stray HUD GameObject), so the
  flagship game now shows a live counter; it still collapses to a single recompile (4 unique scripts:
  player/score/collectible/goal). Aliases skor/puan/hud/points/sayac. Generated C# is pure ASCII
  (replaced a stray em-dash). Doc scripted-table row + §1 collectathon row updated (no-phantom guard
  still green). +6 score tests; updated the 2 collectathon grouping assertions (now 4 unique / 6-7
  attachments). Live-proved the generated AutopilotScore.cs + decoupled collectible + HUD wiring
  (pure, execute=False; no recompile triggered). — tests: 312 passed
- [cycle 30] Filled ALL remaining scripted-behaviour templates. Seven behaviours were declared in
  `NEEDS_SCRIPT` but had no MonoBehaviour source (they reported `needs_script` with nothing to attach):
  `bob` (AutopilotBob — sine bob around start), `bounce` (AutopilotBounce — abs-sine, never dips below
  rest), `patrol` (AutopilotPatrol — PingPong/Lerp between start and a point `distance` along an axis),
  `follow`/`chase` (AutopilotFollower — FindWithTag("Player") then MoveTowards, stops short, no-op if
  no player), `orbit` (AutopilotOrbit — RotateAround its start point), `wander` (AutopilotWander —
  drifts to random points near home, re-targeting on a timer). All reuse the existing
  `__CLASS__/__AX__/__AY__/__AZ__/__SPEED__` placeholder scheme via `_SCRIPT_TEMPLATES`. Verified every
  generated source is pure ASCII, brace- and paren-balanced, with every placeholder substituted; now
  NO NEEDS_SCRIPT behaviour is left without a template. Doc scripted-table lists them all and the
  "Declared but not yet templated" note is retired (no-phantom guard still green). TR aliases
  devriye→patrol, takip→follow, zıpla→bounce resolve to real templates. +13 tests. Live-proved the
  generated AutopilotPatrol.cs + AutopilotFollower.cs + the empty backlog (pure, execute=False; no
  recompile triggered). — tests: 325 passed
- [cycle 31] Chase blueprint — the 5th game type, and the first to put a cycle-30 behaviour to work in
  a real game. `core/game_blueprint.plan_chase_game`: ground + a tagged WASD player carrying the score
  HUD + N enemies that CHASE the player (each composes `follow` — FindWithTag + MoveTowards — with
  `killzone`, the same two-behaviour trick the dodge game uses for moving hazards, so touching an enemy
  respawns you) + a tighter ring of `collectible`s to grab while escaping (+1 each to the HUD) + a goal.
  Registered in BLUEPRINTS as `chase`; `plan_unity_fast_action` routes "kovalamaca", "takip oyunu",
  "chase game" → game_type=chase (the other game intents unchanged; behaviour-name `chase` and
  game-type `chase` live in separate namespaces, no collision). Six unique scripts
  (player/score/follow/killzone/collectible/goal) still collapse to a single recompile via
  `group_execution_plan`. Doc §1 table row + §3 intent phrases (no-phantom guard still green). +8 tests
  (structure, enemy follow+killzone combo, collectibles+goal, count clamp, catalog, grouping, intent
  routing, other-intents-unchanged). Live-proved the plan + 4 intent phrases (pure, execute=False; no
  recompile triggered). — tests: 333 passed
- [cycle 32] Living scenes — decorative behaviours as scene juice (not a game). `plan_ambient_decor`
  (pure, in core/game_blueprint.py) places N props (default Sphere, circle) and cycles the decor set
  `bob/orbit/rotate/wander` over them so the scene breathes; there is deliberately no player/goal.
  Custom `behaviours` subsets are normalized through the alias table and validated against the template
  registry (e.g. "don"->rotate kept, "teleport" dropped), falling back to the default set if nothing
  valid remains — the plan can never reference a behaviour without a template. New tool
  `unity_animate_group` wraps the planner with the same execute=False (plan only, default) /
  execute=True (build + a single recompile) contract as the games; `plan_unity_fast_action` routes
  "sahneyi canlandır", "yaşayan sahne", "animate the scene", "dekoratif animasyon" -> unity_animate_group
  (a non-game intent branch, separate from build-game). Refactor: the live build->import->wait->attach
  path is now a shared `_execute_grouped_behaviour_plan` helper used by BOTH unity_build_simple_game and
  unity_animate_group (de-dup; unity_build_simple_game's behaviour is unchanged and its execute/import-
  count tests still pass). Doc §6 "Living scenes" added (no-phantom guard still green; unity_animate_group
  is registered). +9 tests. Live-proved the decor plan + alias validation + dry-run + 4 intent phrases
  (pure, execute=False; no recompile triggered). — tests: 342 passed
- [cycle 33] Game QA / readiness — pure, bridge-free self-analysis. New `core/game_qa.py`:
  `summarize_plan(plan)` counts objects (`unity_create_primitive`=1, `unity_place_primitives`=count,
  `unity_set_tag`=0) and behaviours (both scripted `script_behaviour` steps and physics
  `unity_add_gameplay_behaviour` steps, e.g. platformer's static_obstacle). `assess_game_readiness(plan)`
  builds on it: has_player/has_goal/has_score, collectible_count, hazard_count (killzone),
  unique-script count (via group_execution_plan), a **playable** verdict (player AND at least one
  interactive behaviour from goal/collectible/killzone/mover/follow/chase/spawner/patrol), and a
  warnings list ("empty scene", "no player", "no goal", "collectibles but no score HUD", "not
  playable"). New tool `unity_assess_game(game_type, collectible_count)` runs the whole thing with NO
  bridge so the studio can sanity-check a game before building. Verified across the catalog: all 5
  blueprints report playable=True (survival also warns "no goal" — correct, it's survive-don't-die);
  ambient decor correctly reports playable=False with player/goal warnings. +15 tests. Live-proved a
  readiness table for every game type + decor (pure). — tests: 357 passed
- [cycle 34] Bound game QA to natural language. `plan_unity_fast_action` gained an assess branch:
  "oyunu değerlendir", "analiz et", "oynanabilir mi", "oyun QA / QA yap", "assess the game", "is the
  game playable", "hazır mı" -> unity_assess_game (read-only, pure). Crucially the assess branch is
  evaluated BEFORE the build branch, because a prompt like "dodge oyununu değerlendir" contains both a
  game type AND an assess verb — the user wants an analysis, not a rebuild; assess wins. It also
  requires a game context ("oyun"/"game"), so scene-level "analiz" / "qa" / "performans" prompts (no
  game) still fall through to the existing visual-QA (`unity_run_visual_qa`) and profiling
  (`unity_profile_scene_performance`) branches — verified they are not hijacked. Refactor: the
  game-type detection (dodge/survival/platformer/chase/collectathon) is now a shared
  `detect_game_type()` closure used by BOTH the build and assess branches (replaced the duplicated
  if/elif chain). Doc §3 assess note. +6 tests (assess routing + game_type extraction, assess-beats-
  build, build-still-builds, scene-analysis-not-hijacked, read-only). Live-proved NL -> assess intent
  -> real readiness report end-to-end (pure, no bridge). — tests: 368 passed
- [cycle 35] Game variation generator. `core/game_blueprint.plan_game_variations(game_type, counts,
  arena_size)` builds the SAME game type at several counts and attaches a readiness summary to each, so
  the studio can offer difficulty options (default counts 3/5/8 -> easy/medium/hard labels) before
  committing to a build. Counts are deduped, clamped (>=1) and sorted ascending so difficulty rises
  monotonically — more enemies/collectibles means strictly more objects. Each variation reports
  {label, params:{count, arena_size}, summary, object_count, unique_scripts, playable, warnings}; it
  reuses game_qa.assess_game_readiness (lazy import to avoid the game_blueprint<->game_qa import cycle).
  New pure tool `unity_game_variations(game_type, counts="3,5,8", arena_size)` exposes it with NO bridge.
  Verified every variation of all 5 blueprints is playable and object counts increase strictly with
  count. Doc §6 "Difficulty variations". +14 tests. Live-proved 3 variations each for chase/collectathon
  + a custom dodge 2/5/10 sweep (pure, no bridge). — tests: 382 passed
- [cycle 36] Bound difficulty + variations to natural language. (a) A `difficulty_count()` closure in
  plan_unity_fast_action maps a difficulty WORD to the build count — kolay/easy/basit→3, orta/normal/
  medium→5, zor/hard/difficult/zorlu→8 — but an explicit number always wins (`re.search` for a digit
  short-circuits to _infer_count). "cok" is deliberately NOT a trigger: it's a quantity word ("cok
  dusman"=many enemies), and "cok zor" still matches "zor". The build branch now uses difficulty_count
  instead of a bare _infer_count. (b) A new variations intent ("varyasyon", "secenek*", "farkli
  zorluk", "variations", "easy medium hard" + a game context) routes to unity_game_variations and is
  checked BEFORE the build branch, so "dodge varyasyonlari goster" lists the easy/medium/hard options
  rather than building one dodge ("secenek" is a single-token prefix so it catches "secenekleri" even
  after "oyunu"). Verified the existing build/assess intents are unchanged. Doc §6 intent note. +19
  tests (difficulty->count table, explicit-number priority, variations routing + game_type, variations-
  beats-build, cok-not-a-trigger). Live-proved difficulty build counts + variation routing (pure).
  — tests: 401 passed
- [cycle 37] Game catalog — the studio's one-glance "what can I make?" report. `core/game_qa.summarize_catalog(count)`
  walks every blueprint in BLUEPRINTS, plans + assesses each, and returns {ok, game_count, games:[per-game
  game_type/summary/object_count/unique_scripts/playable/has_player/has_goal/has_score/warnings], all_playable,
  unique_behaviours, behaviour_count}. Games are sorted for stable output; behaviours are the union across the
  whole catalog. New pure tool `unity_game_catalog` (NO bridge) exposes it; `plan_unity_fast_action` routes
  "oyun katalogu", "oyun listesi/turleri/cesitleri", "hangi oyunlar", "neler yapabilir", "what games", "list
  games" -> unity_game_catalog — keyed on game-scoped phrases so bare "katalog"/"sahne katalogu" still reaches
  the scene catalog (`unity_get_scene_catalog`), verified not hijacked. Live: all 5 games playable, 9 unique
  behaviours across the catalog. Doc §7. +14 tests. Pure + deterministic, no scene changes. — tests: 415 passed
- [cycle 38] Injected the studio's game-making capabilities into the master planner prompt.
  `core/game_qa.build_game_capabilities_summary()` renders a compact block listing the game types and
  the tool each request routes to (build->unity_build_simple_game, assess->unity_assess_game,
  variations->unity_game_variations, catalog->unity_game_catalog), the available behaviour set, and the
  execute=False/True recompile note. It is CODE-DERIVED (reads summarize_catalog, not a hardcoded list)
  so it stays current as blueprints/behaviours grow. `DualAgentOrchestrator._build_master_prompt` now
  appends this block (between the learned-pattern section and the planning instructions) inside a
  defensive try/except so a failure here can never break planning. Now the LOCAL LLM master planner is
  aware it can make 5 games and how to route each request — closing the gap where the deterministic
  fast-path knew about games but the LLM planner did not. +4 tests (summary lists all types + tool names,
  is code-derived not hardcoded, is actually injected into a real _build_master_prompt call). Live-proved
  the generated capability text. — tests: 419 passed
- [cycle 39] Landing / README doc. `docs/GAME_STUDIO.md` is the one-screen entry point to the whole
  studio: WHAT it makes (a 5-game table: collectathon/dodge/survival/platformer/chase + living scenes),
  HOW to drive it (a natural-language → tool table covering build / difficulty / assess / variations /
  catalog / animate), the architecture as an ASCII pipeline (NL -> plan_unity_fast_action -> blueprint
  -> group_execution_plan -> execute=False plan or execute=True build), the safety model (execute=False
  default, recompile note, pure planning/QA tools), and links to every sibling doc
  (GAMES/TOOLS/ARCHITECTURE/ROADMAP/PROGRESS). Kept it summary+signpost so it does not duplicate the
  deep docs. Guarded by `tests/test_landing_doc.py`: every game type and unity_* tool it names is real
  (registry/BLUEPRINTS), and the sibling links are present. Verified all 5 game types + 5 tool
  references + sibling links resolve against the live code. +5 tests. Docs only, no behaviour change.
  — tests: 424 passed
- [cycle 40] STATE REVIEW + new big goal P8 = SAVE/LOAD. Reviewed P0-P7 (all done; the studio is a
  working game maker: 5 game types, full behaviour catalog, score/HUD, living scenes, QA, variations,
  catalog, NL intent, master-prompt injection, landing doc; tests 84->424). Picked game PERSISTENCE as
  the next big goal — every game was ephemeral (built then forgotten, unsaveable/unshareable), and
  save/load unblocks a game library, multi-level packs, procedural seeds, and tuning history (chosen
  over a new game type / parameter tuning / level editor, which depend on it). First step shipped:
  `core/game_io.py` — `serialize_plan(plan, pretty=)` wraps a plan in a versioned JSON envelope
  (schema "unitytools.game_plan" v1 + kind/name/step_count), `deserialize_plan(text)` validates the
  envelope (schema, not-future version, a real steps list) and returns the EXACT plan back,
  `plan_metadata(text)` reads just the header. New pure tool `unity_export_game(game_type, count)` (NO
  bridge) returns the serialized JSON. Verified zero-loss round-trip for every blueprint + decor plan,
  rejection of junk/forged/future-version input, and an end-to-end export->load-back of a platformer.
  +15 tests. Roadmap P8 section added with the next steps (disk save/load via safe_contained_path,
  saved-game library, import+replay). Pure + deterministic, no disk, no scene changes. — tests: 439 passed
- [cycle 41] P8 step 2: SAVE/LOAD to disk (safely). `core/game_io.py` gained `save_plan_to_file(plan,
  name, root)`, `load_plan_from_file(name, root)`, `list_saved_games(root)`, plus `sanitize_game_name`
  and `default_games_dir` (env UNITYTOOLS_GAMES_DIR else <cwd>/.unitytools/games). Path-traversal is
  blocked by TWO independent layers: (1) the name is sanitized to a slug — every char outside
  [A-Za-z0-9_-] (including '.', '/', '\\') becomes '_', leading/trailing '.'/'_' stripped, empty
  rejected, capped at 64 — and (2) the resulting `<slug>.json` is re-resolved through the existing
  `safe_contained_path`, which raises if it would land outside the games root. So "../../etc/passwd"
  saves as "etc_passwd.json" INSIDE the root and ".." is rejected outright. New tools: `unity_save_game`
  (plans + writes, no scene change), `unity_load_game` (returns the PLAN only — does NOT build/execute
  it), `unity_list_saved_games` — all pure, no bridge. No file deletion this cycle (write/read/list
  only). +17 tests (sanitization table, disk round-trip via tmp_path, sorted listing, missing->error,
  traversal-stays-inside-root, env-pointed tool flow). Live-proved save->list->load round-trip and the
  traversal defense. — tests: 456 passed
- [cycle 42] P8 step 3: save/load/list NL intents. `plan_unity_fast_action` gained three game-scoped
  branches, checked BEFORE build/assess/variations/catalog: (a) "oyunu kaydet" / "X olarak kaydet" /
  `save the game as Y` / `kaydet "name"` -> unity_save_game; (b) "oyunu yukle X" / "X oyununu yukle" /
  "load game X" -> unity_load_game (returns the plan only, write=False); (c) "kayitli oyunlar" /
  "saved games" / "diskteki oyunlar" -> unity_list_saved_games. A pure `extract_game_name(text)` helper
  parses the name from quotes, English "as X", Turkish "X olarak", a verb-prefix (kaydet/yukle/save/load
  + optional game/oyun filler), or an "X oyununu" possessive; a stopword set keeps connectors/verbs
  ("ve", "and", "deney", "game", ...) from being mistaken for a name. The branches require a game context
  (oyun/game or a game-type word) OR an explicit name, so scene-level "save my work" / "sahneyi geri
  yukle" and the "deney kaydet ve ogren" experiment-record intent are NOT hijacked (caught + fixed a
  regression where "kaydet ve ogren" parsed "ve" as a name). "kayitli oyunlar" (disk) stays distinct
  from "hangi oyunlar" (catalog). Doc §3 note. +21 tests (extract_game_name table, save/load/list
  routing, difficulty-on-save, no-collision, scene-not-hijacked). Live-proved NL kaydet->listele->yukle
  end-to-end. — tests: 477 passed
- [cycle 43] P8 step 4: import + build-from-plan, treating external JSON as untrusted.
  `game_io.validate_plan(plan, max_steps=5000)` structurally validates a (possibly hostile) plan: every
  step must be exactly one of a WHITELISTED tool call (`ALLOWED_PLAN_TOOLS` = create_primitive /
  place_primitives / set_tag / add_gameplay_behaviour) with a flat str->primitive kwargs dict, or a
  `script_behaviour` whose behaviour has a real template; a forged/unknown tool, nested/non-primitive
  kwargs, a step with both or neither key, an unknown behaviour, or too many steps is rejected with the
  offending index. New tools: `unity_import_game(json_text)` (deserialize_plan + validate_plan, returns
  the plan but never builds — so a malicious file cannot make the studio call arbitrary tools) and
  `unity_build_loaded_game(name, execute=False)` which LOADS a saved game, RE-VALIDATES it (defense in
  depth — even our own saves), then builds via the shared `_execute_grouped_behaviour_plan`;
  execute=False (default) is a safe validated dry-run, execute=True builds and triggers the single
  recompile. +20 tests (validate accepts all 5 blueprints + decor; rejects non-whitelisted tool,
  unknown behaviour, non-primitive kwargs, both/neither, non-dict, missing steps, >max; import accepts
  valid / rejects bad-json + forged-tool; build-from-plan dry-run + real execute via a fake bridge).
  Live-proved import accepting a real game, rejecting a forged `os_system` step at index 1, and a
  save->load->validate->build dry-run. — tests: 497 passed
- [cycle 44] P8 step 5: made the save/load/import capabilities visible everywhere. (a)
  `game_qa.build_game_capabilities_summary()` now includes two lines for persistence — save ->
  unity_save_game, load -> unity_load_game, list -> unity_list_saved_games, import (validated) ->
  unity_import_game, build a saved game -> unity_build_loaded_game — so the LOCAL LLM master planner
  (which is fed this block) knows games can be saved/loaded/imported. (b) `docs/GAME_STUDIO.md` landing
  gained a "Persistence" section: NL examples (kaydet/yukle/kayitli oyunlar) plus the safety model
  (sanitize + safe_contained_path two-layer traversal defense, validate_plan for external JSON,
  execute=False default). (c) `GAME_STUDIO_TOOLS.md` got a persistence tool table. The capability-summary
  and landing-doc guards were extended to assert the five persistence tool names are real (registry). All
  references verified live. +1 test. Docs/summary only, no behaviour change. — tests: 498 passed
- [cycle 45] STATE REVIEW + new big goal P9 = PROCEDURAL GENERATION. Reviewed P8 (save/load) — complete
  across 5 steps (serialize/deserialize, safe disk save/load, NL intent, validated import, build-from-
  plan, visibility); tests 424->498. Picked reproducible procedural variety as the next big goal: today
  difficulty only changes the count and layouts are fixed, so games of the same type look alike. First
  step shipped: `core/procedural.py` — `seeded_rng(seed)` is a pure splitmix64 RNG (SHA-256 the seed to a
  64-bit state, then splitmix64; exposes random/uniform/randint(inclusive)/choice/shuffle), DETERMINISTIC
  with NO system time or global random — so seeds are byte-for-byte reproducible and shareable.
  `plan_game(game_type, count, seed=...)` now post-processes the plan (via a new `_apply_seed`, WITHOUT
  editing any blueprint) to record the seed and give each placement step a reproducible `jitter`: same
  seed ⇒ identical plan, different seed ⇒ different-but-deterministic, seed=None ⇒ the plain blueprint
  (all existing blueprint tests unaffected). `unity_build_simple_game` gained a `seed` param. Seeded
  plans still pass validate_plan (jitter is a primitive kwarg) and assess as playable. Roadmap P9 section
  added. +14 tests (RNG determinism/bounds/coverage, choice/shuffle, seeded-plan reproducibility,
  seed=None no-op, validate+playable, build tool). Live-proved same-seed-same-game across calls. No
  Math.random / new Date — fully deterministic. — tests: 512 passed
- [cycle 46] P9 step 2: the seed now reaches the LAYOUT (not just jitter). `core/procedural.py` gained
  two pure deterministic helpers — `seeded_pick(seed, options)` and `seeded_positions(seed, count,
  area)`. `game_blueprint._apply_seed` was extended: every `unity_place_primitives` step now gets a
  seed-chosen pattern (scatter/circle/grid), a seed-scaled spacing, and jitter; and a platformer's
  `Platform_i` cubes get a lateral x-only shift (-2.5..2.5) with the Goal re-aligned to the LAST
  platform's x — position_y and position_z (the staircase climb) are deliberately left untouched, so the
  platformer stays strictly monotone in y/z and the goal stays reachable on top. Critically, object
  COUNTS and behaviours are never changed, so every seed still passes validate_plan and assesses as
  playable; seed=None remains a no-op (identical plain plan), and same seed gives an identical plan.
  +58 tests (seeded_pick/positions determinism+bounds, pattern/spacing differ by seed, platformer climb
  monotone across 8 seeds, valid+playable for all 5 games x 8 seeds, object_count seed-independent,
  determinism, seed=None no-op). Live-proved different seeds give different layouts while all stay
  playable. Still no Math.random / new Date. — tests: 570 passed
- [cycle 47] P9 step 3: seed in natural language + persistence. A pure `extract_seed(text)` helper in
  game_studio_actions recognises "tohum 42" / "seed 42" / "seed:abc" / "seed=7" (keyword then value,
  requiring a real separator so the Turkish possessive "tohumu" isn't split into "tohum"+"u") and "42
  tohumu ile" / "forest tohumuyla" (value then keyword), returning (seed, text_with_seed_removed). The
  build branch extracts the seed FIRST and feeds the seed-stripped text to difficulty_count, so a seed
  digit is never mistaken for the count: "zor dodge oyunu kur tohum 7" -> dodge, count=8 (hard), seed=7;
  "dodge oyunu yap 5 tohum 12" -> count=5, seed=12. The seed is added to unity_build_simple_game's kwargs
  only when present. Confirmed the seed already travels inside the plan dict, so it survives both
  serialize/deserialize and disk save/load with no extra work (round-trip tested). Capability summary
  (so the master planner knows about seeds) + GAMES.md note added. +18 tests (extract_seed pattern table,
  seed-vs-count separation, explicit-count+seed coexist, no-seed no-kwarg, word seeds, seed survives
  serialize + disk round-trip). Live-proved NL "tohum 7" -> seed 7 (count 8), same seed -> same game,
  seed preserved in JSON. Deterministic. — tests: 588 passed
- [cycle 48] STATE REVIEW + new big goal P10 = MAZE GAME TYPE. Reviewed P0-P9 (the studio is a
  self-operating game maker: 5 game types, full behaviour catalog, score/HUD, living scenes, QA,
  variations, catalog, persistence, procedural seeds; tests 84->588). User delegated the P10 choice;
  picked a procedural maze/labyrinth game type — the canonical use of the new seed machinery, reusing
  the existing behaviour/blueprint/QA stack. First step: `core/maze.py` — `generate_maze(seed, width,
  height)` builds a PERFECT maze via a seeded recursive backtracker (iterative DFS over a (2h+1)x(2w+1)
  wall grid, neighbour chosen by seeded_rng), giving a spanning tree over all cells: deterministic (same
  seed=>same maze) and ALWAYS solvable (exactly one path between any two cells). Returns the '#'/' '
  grid + entrance (0,0) / exit (w-1,h-1). `maze_is_solvable` is an INDEPENDENT BFS that proves
  solvability (and guards a malformed/imported maze); `maze_wall_positions` maps the grid to Unity cube
  (x,z) positions for the upcoming blueprint. Pure, no system time / Math.random. +72 tests (dimensions,
  all-walls border, size clamp 1..25, determinism, ALWAYS-SOLVABLE across 8 seeds x 7 sizes incl 1x1 and
  25x25, perfect-maze passage count 2*W*H-1, broken-maze detection, wall-position mapping + origin).
  Additionally ran a two-adversary independent verification workflow (each adversary wrote its OWN
  solver/structure checker and brute-forced many seeds/sizes). Live-rendered a real solvable maze.
  — tests: 660 passed
- [cycle 49] P10 step 2: maze blueprint — the 6th game type. `core/game_blueprint.plan_maze_game(size,
  arena_size, seed)` generates a deterministic perfect maze (core.maze.generate_maze) and lays it out as
  solid wall cubes (each made a `static_obstacle`) on a ground plane, with a WASD+jump player + score
  HUD placed on the entrance cell and a goal on the exit cell (world positions computed from the cell ->
  grid -> world mapping, so neither overlaps a wall). The seed is used at GENERATION time: plan_game now
  special-cases `maze` to pass the seed straight to the planner (rather than the place_primitives-jitter
  path of _apply_seed, which a maze has none of), and the seed is recorded on the plan so it survives
  save/load. Registered in BLUEPRINTS (6 games now: collectathon/dodge/survival/platformer/chase/maze).
  Size clamped 3..8 to keep object counts sane (5x5 = 72 walls/75 objects, 8x8 = 162 walls/165 objects,
  well under the 500 ceiling). Every seed passes validate_plan (walls are whitelisted create_primitive +
  static_obstacle tool steps) and assesses as playable (player+goal); plan_game_variations also works
  for maze (varies size). Added a maze row to the landing doc so the no-phantom landing guard stays
  green. +13 tests (registration, structure, valid+playable per seed, determinism + seed recorded, size
  clamp + object-count bound, player/goal-not-in-wall, player/goal on entrance/exit cells, one-recompile
  grouping, variations). Live-rendered a 5x5 maze game with P at the entrance and G at the exit.
  — tests: 686 passed
- [cycle 50] P10 step 3: maze natural-language intent + docs. `detect_game_type` gained a maze branch
  (maze/labirent -> "maze") and `wants_game` learned "maze"/"labirent"/"maze game"/"labirent oyunu", so
  "labirent oyunu kur" / "build me a maze game" route to a maze build. Because maze reuses the shared
  detect_game_type, assess ("labirent oyununu degerlendir") and variations ("labirent varyasyonlari
  goster") recognise it too. Size (collectible_count -> maze size) and seed work together: "labirent
  oyunu kur 6 tohum 7" -> game_type=maze, size 6, seed 7 (extract_seed strips the seed so it is not read
  as the size). GAME_STUDIO_GAMES.md §1 gained a maze row + intent phrases (no-phantom doc guard updated
  to assert maze in BLUEPRINTS + doc). The code-derived build_game_capabilities_summary now reports "6
  playable game types" and lists maze automatically (verified). The other five game intents are
  unchanged. +10 tests (maze build per phrasing, size+seed together, seed-only, assess+variations,
  others-unchanged, capability summary lists maze). Live-proved NL maze build (size+seed) end-to-end.
  — tests: 696 passed