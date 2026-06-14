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