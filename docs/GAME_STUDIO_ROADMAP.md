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
- [x] Platformer blueprint (cycle 28): `plan_platformer_game` — ground + WASD+**jump** player + N
  solid platforms climbing like a staircase (increasing y & z, made solid with the `static_obstacle`
  physics behaviour — no recompile) + a goal on top reached by jumping up. Registered as the 4th game
  type; routed by intent (platform / zıplama oyunu / platformer / jump game → game_type=platformer).
  Doc table + 8 tests. Catalog now has 4 games. **Remaining:** in-game score/HUD, fill the
  not-yet-templated behaviours (follow/patrol/bob).
- [x] Score / HUD (cycle 29): `score` scripted behaviour → `AutopilotScore` MonoBehaviour — a global
  `static int Score`, a top-left `OnGUI` HUD, and both a `static Add(n)` helper and a `SendMessage`
  target `AddScore(n)`. The collectible now signals a +1 on pickup via
  `SendMessage("AddScore", 1, DontRequireReceiver)` — no hard type reference, so it stays
  self-contained (compiles with or without a HUD). The collectathon blueprint attaches `score` to the
  Player so the flagship game shows a live counter (still one recompile: player/score/collectible/goal).
  Aliases skor/puan/hud/points/sayac. Generated source is pure ASCII. Doc row + 6 tests.
  **Remaining:** fill the not-yet-templated behaviours (follow/patrol/bob), HUD beyond score (timer/lives).
- [x] Motion behaviour templates (cycle 30): templated ALL 7 remaining `needs_script` behaviours —
  `bob` (AutopilotBob, sine bob), `bounce` (AutopilotBounce, abs-sine), `patrol` (AutopilotPatrol,
  PingPong between two points), `follow`/`chase` (AutopilotFollower, MoveTowards the Player tag,
  no-op if absent), `orbit` (AutopilotOrbit, RotateAround), `wander` (AutopilotWander, random drift).
  Every NEEDS_SCRIPT behaviour now generates a compilable, pure-ASCII, balanced MonoBehaviour — no
  stubs left. Doc scripted-table now lists them all ("Declared but not yet templated" note retired).
  +13 tests (per-behaviour ASCII/balance/placeholder-substitution, class names, key idioms, TR aliases
  devriye/takip/zıpla). **Remaining:** use these in a blueprint or fast-action intent (cycle 31).
- [x] Chase blueprint (cycle 31): `plan_chase_game` — the 5th game type, the first to use a cycle-30
  behaviour in a real game. Ground + player (tag + controller + score HUD) + N enemies that **chase**
  the player (`follow` + `killzone` composed, the dodge trick) + a ring of `collectible`s to grab while
  escaping + a goal. Registered as `chase`; routed by intent (kovalamaca / takip oyunu / chase game →
  game_type=chase). 6 unique scripts collapse to one recompile. Doc §1 row + intent phrases + 8 tests.
  Catalog now has 5 games. **Remaining:** decorative behaviours (bob/orbit) in a scene/blueprint
  (cycle 32); a game summarizer / readiness QA report (cycle 33).
- [x] Living scenes (cycle 32): decorative behaviours as scene juice. `plan_ambient_decor` (pure)
  places N props and cycles `bob/orbit/rotate/wander` over them — a scene that breathes, not a game
  (no player/goal). Custom subsets are normalized + validated (unknown names dropped, never phantom).
  New tool `unity_animate_group` wraps it with the same execute=False(plan)/execute=True(build, one
  recompile) contract; routed by intent (sahneyi canlandır / yaşayan sahne / animate the scene). The
  build→import→wait→attach path was extracted into a shared `_execute_grouped_behaviour_plan` helper
  (de-dups unity_build_simple_game; behaviour unchanged — its tests still pass). Doc §6 + 9 tests.
  **Remaining:** game summarizer / readiness QA report (cycle 33).
- [x] Game QA / readiness (cycle 33): `core/game_qa.py` — pure, bridge-free analysis of a blueprint
  plan. `summarize_plan` counts objects (create=1, place=count, set_tag=0) and behaviours (scripted +
  physics); `assess_game_readiness` adds has_player/has_goal/has_score, collectible/hazard counts,
  unique-script count, a **playable** verdict (player + an interactive element), and warnings ("no
  goal", "collectibles but no score HUD", "not playable", …). New tool `unity_assess_game` (pure, no
  bridge) runs it for a game_type so the studio can sanity-check a game before building. Every one of
  the 5 blueprints reports playable=True; decor reports not-playable (correctly). +15 tests.
  **Remaining:** bind QA to the NL/master-planner intent (cycle 34); a game-variation generator
  (same type, different parameters) (cycle 35).
- [x] Assess intent (cycle 34): `plan_unity_fast_action` now routes "oyunu değerlendir" / "analiz et"
  / "oynanabilir mi" / "assess the game" / "is the game playable" → `unity_assess_game` (read-only).
  The assess branch is checked **before** the build branch and requires a game context ("oyun"/"game"),
  so "dodge oyununu değerlendir" is analysed (not rebuilt) while scene-level "analiz"/"qa"/"performans"
  still reach the visual-QA / profiling branches. Refactor: the game-type detection is now a shared
  `detect_game_type()` helper used by both the build and assess branches (de-dup). Doc §3 note + 6
  tests. **Remaining:** a game-variation generator (same type, different parameters) (cycle 35).
- [x] Game variations (cycle 35): `plan_game_variations(game_type, counts, arena_size)` builds the
  same game at several counts (default 3/5/8 → easy/medium/hard) and attaches a readiness summary to
  each — difficulty options the studio can offer before building. Counts are deduped/clamped/sorted so
  difficulty rises monotonically (more objects). New pure tool `unity_game_variations` (no bridge).
  Every variation of every blueprint is playable. Doc §6 + 14 tests. **Remaining:** bind difficulty
  to NL ("kolay/zor oyun") (cycle 36); a one-glance catalog report (all types + readiness) (cycle 37).
- [x] Difficulty + variations intents (cycle 36): `plan_unity_fast_action` now reads difficulty —
  kolay/easy→3, orta/normal→5, zor/hard→8 set the build count (an explicit number still wins; "çok" is
  not a trigger). A new variations intent ("varyasyon" / "seçenekler" / "farklı zorluklar") routes to
  `unity_game_variations`, checked before the build branch so "dodge varyasyonları göster" lists the
  options instead of building. Doc §6 intent note + 19 tests. **Remaining:** a one-glance catalog
  report (all types + readiness) (cycle 37); inject game capabilities into the master planner (cycle 38).
- [x] Game catalog (cycle 37): `core/game_qa.summarize_catalog()` walks every blueprint, plans +
  assesses each, and returns a one-glance "what can I make?" report — per-game summary/counts/playable
  verdict/warnings, plus the union of behaviours used and an `all_playable` flag. New pure tool
  `unity_game_catalog` (no bridge); routed by intent ("oyun katalogu" / "hangi oyunlar" / "neler
  yapabilirsin" / "what games" / "list games") while bare "katalog" still means the scene catalog.
  Doc §7 + 14 tests. **Remaining:** inject game capabilities into the master planner (cycle 38);
  a one-page studio README/landing doc (cycle 39).
- [x] Master-planner capability injection (cycle 38): `game_qa.build_game_capabilities_summary()`
  renders a compact, CODE-DERIVED block (from summarize_catalog, not hardcoded) listing the 5 game
  types and the tool each request routes to (build→unity_build_simple_game, assess→unity_assess_game,
  variations→unity_game_variations, catalog→unity_game_catalog) plus the behaviour set and the
  execute/recompile note. `DualAgentOrchestrator._build_master_prompt` injects it (defensive try/except)
  so the planner knows it can make games. +4 tests. **Remaining:** a one-page studio README/landing doc
  (cycle 39); a state review to pick the next big goal — multiplayer? save/load? level editor? (cycle 40).
- [x] Landing doc (cycle 39): `docs/GAME_STUDIO.md` — the one-screen entry point. What it makes (5-game
  table), how to drive it (NL command → tool table), an ASCII architecture diagram (NL → blueprint →
  group_execution → execute), the safety model (execute=False default, recompile note), and links to all
  sibling docs. Guarded by `tests/test_landing_doc.py` (every game type + unity_* tool named is real,
  sibling links present). +5 tests. **Remaining:** state review + pick the next big goal (cycle 40).

### P8 — Game persistence (save / load), then a game library
**Cycle-40 state review.** P0–P7 are done: the studio is a working game maker — 5 playable game types
(collectathon/dodge/survival/platformer/chase), a complete behaviour catalog (physics + scripted, no
stubs), score/HUD, living scenes, readiness QA, difficulty variations, a catalog report, full NL intent
routing, master-planner capability injection, and a landing doc. Tests grew 84 → 439.

The biggest remaining gap: **every game is ephemeral.** A plan is built and forgotten — it can't be
saved, shared, versioned, or replayed. P8 makes games **persistent**, which also unblocks a game
library, multi-level packs, procedural seeds, and tuning history. Chosen over a new game type (marginal),
parameter-tuning (needs persistence to store history), or a level editor (needs save/load first).

- [x] Save/load core (cycle 40): `core/game_io.py` — `serialize_plan(plan)` → a versioned JSON envelope
  (schema/version/kind/name/step_count + plan), `deserialize_plan(text)` → the exact plan back
  (round-trip safe, validates schema/version, rejects junk), `plan_metadata(text)` → envelope header
  only. New pure tool `unity_export_game(game_type)` (no bridge). Round-trips every blueprint + decor
  with zero loss. +15 tests. **Next:** save/load to disk via `safe_contained_path` (cycle 41); a saved-
  game library / list+load by name (cycle 42); `unity_import_game` + replay an imported plan.
- [x] Disk save/load (cycle 41): `core/game_io.py` gained `save_plan_to_file(plan, name, root)`,
  `load_plan_from_file(name, root)`, `list_saved_games(root)`, and `sanitize_game_name`/`default_games_dir`
  (env `UNITYTOOLS_GAMES_DIR` else `.unitytools/games`). TWO-LAYER path-traversal defense: the name is
  sanitized to a slug (alnum/-/_ only, `.`/`/`/`\` → `_`, empty rejected) AND the final path is re-guarded
  with `safe_contained_path`, so no name can escape the games root. New tools `unity_save_game`,
  `unity_load_game` (returns the plan only — does not build), `unity_list_saved_games` (all pure, no
  bridge; saving never touches the scene). Verified disk round-trip, listing, missing-file errors, and
  that `../../etc/passwd` lands inside the root. +17 tests. **Next:** saved-game library + NL intent
  (kaydet/yükle/kayıtlı oyunlar) (cycle 42); `unity_import_game` + replay an imported plan (cycle 43).
- [x] Save/load NL intents (cycle 42): `plan_unity_fast_action` now routes save/load/list to the disk
  tools. "oyunu kaydet" / "X olarak kaydet" / `save as Y` → `unity_save_game` (name from quotes / "as X"
  / "X olarak", else game type); "oyunu yükle X" / "load X" → `unity_load_game` (returns the plan only);
  "kayıtlı oyunlar" / "saved games" → `unity_list_saved_games`. A pure `extract_game_name` helper does
  the name parsing. These are checked before build/assess/variations/catalog (distinctive verbs) and
  require a game context so scene-level "save"/"geri yükle" and the "deney kaydet" experiment intent are
  not stolen. Doc §3 note. +21 tests. **Next:** `unity_import_game` (validate + load external JSON) +
  a build-from-plan path to actually construct a loaded game (cycle 43); add save/load to the master
  prompt summary + landing doc (cycle 44).
- [x] Import + build-from-plan (cycle 43): `game_io.validate_plan(plan)` treats a plan as UNTRUSTED —
  every step must be a whitelisted tool (`ALLOWED_PLAN_TOOLS`: create_primitive / place_primitives /
  set_tag / add_gameplay_behaviour) with flat-primitive kwargs, or a real templated `script_behaviour`;
  anything else (forged tool, nested kwargs, both/neither, unknown behaviour, >5000 steps) is rejected
  with the offending index. New tools: `unity_import_game(json_text)` (deserialize + validate, returns
  the plan WITHOUT building) and `unity_build_loaded_game(name, execute=False)` (load → re-validate →
  build via the shared `_execute_grouped_behaviour_plan`; execute=False is a safe dry-run, execute=True
  triggers a recompile). +20 tests (accepts all blueprints, rejects hostile input, import/build flow).
  **Next:** surface save/load/import in the master prompt + landing doc + capability summary (cycle 44);
  P8 wrap-up + pick P9 (cycle 45).
- [x] Surface persistence (cycle 44): `build_game_capabilities_summary()` now lists the save/load/list/
  import/build-loaded tools (so the master planner — which is fed this block — knows games can be
  persisted), the landing doc (`GAME_STUDIO.md`) gained a "Persistence" section (NL examples + the
  two-layer traversal defense + validate_plan + execute=False default), and `GAME_STUDIO_TOOLS.md` got a
  persistence tool table. Capability + landing-doc guards updated to assert the new tool names are real.
  +1 test. **Next:** P8 wrap-up + pick P9 (cycle 45) — multi-level/scene save, procedural seed
  generator, autonomous parameter tuning, or a new game type.

### P9 — Procedural generation (reproducible variety)
**Cycle-45 state review.** P8 (save/load) is complete across 5 steps — serialize/deserialize, safe disk
save/load, NL intent, validated import, build-from-plan, and visibility (master prompt + docs). Tests
grew 424 → 498. The studio can now build, assess, vary, persist, share, and rebuild games.

Next gap: **variety is shallow** — difficulty just changes the count, and layouts are fixed. P9 adds
*reproducible procedural variety*: a seed makes the same game come out the same every time and a
different seed a different one, all **deterministically** (hash-based, no system random/time), so seeds
are saveable/shareable and everything stays unit-testable. Chosen over a level-pack (a thin layer over
P8) and autonomous tuning (needs the seed/variety axis first); a new game type is lower-leverage.

- [x] Seeded RNG + seeded plans (cycle 45): `core/procedural.py` — `seeded_rng(seed)` is a pure
  splitmix64 generator (SHA-256 the seed → splitmix64; random/uniform/randint/choice/shuffle), fully
  deterministic with no system time. `plan_game(game_type, count, seed=...)` post-processes the plan
  (without editing any blueprint) to record the seed and give placement steps reproducible jitter — same
  seed ⇒ identical plan, different seed ⇒ different but deterministic, `seed=None` ⇒ the plain blueprint.
  `unity_build_simple_game` gained a `seed` param. Seeded plans still validate + play. +14 tests.
  **Next:** thread the seed into per-blueprint layout (positions/counts/arena), not just jitter (cycle
  46); expose a seed NL intent ("tohum 42 ile dodge oyunu") + save/share seeds (cycle 47).
- [x] Seed reaches the layout (cycle 46): `core/procedural.py` gained `seeded_pick(seed, options)` and
  `seeded_positions(seed, count, area)` (both pure + deterministic). `_apply_seed` now varies real
  layout: each placement step gets a seed-chosen pattern (scatter/circle/grid), a varied spacing, and
  jitter; a platformer's platforms get a lateral (x-only) shift with the goal re-aligned to the top
  platform — position_y/position_z (the climb) are left intact so it stays strictly monotone and
  reachable. Object counts and behaviours never change, so every seed stays valid (`validate_plan`) and
  playable (`assess`). +58 tests (helpers, pattern/spacing from seed, platformer monotonicity across 8
  seeds, valid+playable for all game×seed combos, count seed-independent, determinism, seed=None no-op).
  **Next:** seed NL intent ("tohum 42 ile dodge oyunu" / "seed 42") + include the seed in save/export
  (cycle 47); P9 wrap-up + pick P10 (cycle 48).
- [x] Seed NL intent + persistence (cycle 47): a pure `extract_seed(text)` helper recognises "tohum 42"
  / "seed 42" / "seed:abc" / "42 tohumuyla" and returns the seed plus the text WITH the seed span
  removed, so the seed digit is never read as the object count (the build branch passes the seed-stripped
  text to `difficulty_count`). "zor dodge oyunu kur tohum 7" → game_type=dodge, count=8 (hard), seed=7;
  the Turkish possessive "tohumu" no longer mis-parses. The build branch adds `seed` to the
  unity_build_simple_game kwargs only when present. Confirmed the seed already rides along in the plan
  dict, so it survives serialize/deserialize AND disk save/load (round-trip tested). Capability summary +
  GAMES.md note added. +18 tests. **Next:** P9 wrap-up + pick P10 (cycle 48).

### P10 — Maze game type (procedural labyrinth)
**Cycle-48 state review.** P0–P9 reviewed: the studio is a self-operating game maker — 5 game types,
full behaviour catalog, score/HUD, living scenes, readiness QA, difficulty variations, catalog,
persistence (save/load/import/build), and reproducible procedural variety (seeded RNG -> layout -> NL +
persistence). Tests 84 -> 660. (Open older polish items remain in P0/P2/P4; not blockers for game-making.)

Chosen next big goal (user-delegated): a **procedural maze/labyrinth game type** — it puts the new
seed/procedural machinery to its best use (maze generation is the canonical seeded-procedural task),
reuses the existing behaviour/blueprint/QA stack, and adds a genuinely new kind of game. Picked over
autonomous parameter tuning (a good follow-on, but a maze is higher-leverage user value) and a
level-pack (a thin layer over P8).

- [x] Maze generator (cycle 48): `core/maze.py` — `generate_maze(seed, width, height)` builds a
  **perfect** maze via a seeded recursive backtracker (a spanning tree over all cells), so it is
  deterministic (same seed => same maze) and **always solvable** (exactly one path between any two
  cells). Returns a `'#'/' '` wall grid + entrance/exit cells. `maze_is_solvable` (independent BFS)
  proves solvability and guards malformed mazes; `maze_wall_positions` maps the grid to Unity cube
  (x,z) positions for the future blueprint. Pure, no system time. +72 tests (dimensions, border, clamp,
  determinism, always-solvable across 8 seeds x 7 sizes, perfect-maze passage count, broken-maze
  detection, wall-position mapping) plus an independent two-adversary verification.
  **Next:** `plan_maze_game` blueprint (walls as static_obstacle cubes + player at entrance + goal at
  exit) + `maze` in BLUEPRINTS (cycle 49); maze NL intent ("labirent oyunu / maze game") + size/seed
  routing (cycle 50).
- [x] Maze blueprint (cycle 49): `plan_maze_game(size, arena_size, seed)` — the **6th game type**. It
  generates a deterministic perfect maze and builds it from solid wall cubes (each a `static_obstacle`),
  a WASD+jump player + score HUD at the entrance, and a goal at the exit. The seed is threaded at
  GENERATION time (plan_game special-cases `maze` to pass the seed to the planner instead of post-hoc
  jitter) and recorded on the plan, so the same seed lays out the same maze and it survives save/load.
  Registered in `BLUEPRINTS`; size clamped 3..8 (5×5 = 72 walls / 75 objects; 8×8 = 162 walls / 165
  objects — well under the 500 ceiling). Every seed is valid (`validate_plan`) and playable (`assess`),
  the player/goal never overlap a wall, and the catalog now has 6 games. Added a maze row to the landing
  doc (keeps the no-phantom guard green). +13 tests. **Next:** maze NL intent ("labirent oyunu kur" /
  "maze game" + size + seed) + GAMES.md/catalog maze row (cycle 50); maze × save/load × variations
  integration + state review (cycle 51).
- [x] Maze NL intent + docs (cycle 50): `detect_game_type` gained a maze branch and `wants_game` learned
  "maze"/"labirent"/"maze game"/"labirent oyunu", so "labirent oyunu kur" / "build me a maze game" route
  to a maze build; size (collectible_count) and seed work together ("labirent oyunu kur 6 tohum 7" ->
  maze, size 6, seed 7), and assess/variations also recognise maze (all via the shared detect_game_type).
  GAMES.md §1 gained a maze row + intent phrases; the code-derived capability summary now reports 6 game
  types and lists maze automatically. The other game intents are unchanged. +10 tests; the no-phantom doc
  guard now asserts maze too. **Next:** maze × save/load × variations × assess end-to-end integration
  (build -> save -> load -> identical maze) + state review (cycle 51).
- [x] Maze end-to-end integration (cycle 51): a full-pipeline test proving the maze works through the
  whole studio — NL intent ("labirent oyunu kur 5 tohum 7") -> plan -> serialize + disk save/load ->
  IDENTICAL plan; the same seed rebuilds the same maze "in another session"; `plan_game_variations`
  across sizes 3/5/7 are all playable with monotonic object counts; assess reports playable+player+goal;
  a re-imported maze plan validates. **P10 (maze) is DONE.** +5 tests.

### P11 — Action-RPG building blocks (combat / RPG flavor) — DONE (cycle 60)
**Closed cycle 60.** A complete blocky action-RPG building-block set: health, attack (melee), ranged
attack, enemy AI, xp/leveling, reward (kill→XP), loot, inventory — plus the `arena` game (7th type)
wiring them into a working loop (armed player vs enemies, kill→XP→level, collect loot→items). Honestly
delivers the action-RPG-FLAVORED prototype the user asked about (KO/V Rising/Remnant 2/Valheim); a real
game at that scale (MMO netcode, AAA art, streaming terrain) stays out of scope, but the mechanics work,
are deterministic, and save/load/seed like every other game.

**Why.** The user asked whether the studio could make a Knight Online / V Rising / Remnant 2 / Valheim
mix. Honest answer (given to them): a real game at that scale — MMO netcode, AAA art/animation, large
streaming terrain — is OUT of scope for this primitive-composition autopilot. But action-RPG-FLAVORED
*building blocks* can be added in the same deterministic MonoBehaviour-template style, toward a blocky
hack-and-slash prototype. Chosen as P11; it extends the existing behaviour catalog (no new architecture).

- [x] Health behaviour (cycle 51): `health` scripted behaviour -> `AutopilotHealth` MonoBehaviour — a
  maxHP/currentHP pair, `TakeDamage(int)` / `Heal(int)` (public, so attack scripts can call them, also
  SendMessage-friendly), death -> respawn at spawn point (or `destroyOnDeath`), and a top-right HP HUD.
  Aliases can/sağlık/hp/health/canlı. Pure ASCII, balanced, every NEEDS_SCRIPT behaviour still templated.
  +5 tests. **Next:** `attack` (melee hit that calls TakeDamage on what it touches) (cycle 52); an enemy
  AI that chases + attacks (follow + attack) (cycle 53); an `arena`/`brawler` blueprint composing player
  + health + armed enemies (cycle 54); later inventory/loot + xp/level.
- [x] Attack behaviour (cycle 52): `attack` scripted behaviour -> `AutopilotAttack` MonoBehaviour — every
  `cooldown` seconds it damages any object tagged `targetTag` within `range` (Physics.OverlapSphere) by
  `SendMessage("TakeDamage", damage, DontRequireReceiver)`. It pairs with `health` (whose TakeDamage(int)
  receives it) but holds NO code reference to AutopilotHealth — a fully decoupled combat chain, so each
  compiles and runs alone. Aliases saldırı/saldır/vur/vuruş/hit. Pure ASCII, balanced. GAMES.md scripted
  table gained health + attack rows (doc guard now generates them too). +10 tests. **Next:** enemy AI
  (follow + attack) (cycle 53); an `arena`/`brawler` blueprint (player+health+armed enemies) as the 7th
  game type (cycle 54); later inventory/loot + xp/level.
- [x] Enemy AI behaviour (cycle 53): `enemy` scripted behaviour -> `AutopilotEnemy` MonoBehaviour —
  chase + attack in ONE: finds the Player by tag, MoveTowards it while out of range, and once within
  `attackRange` stops and attacks on `attackCooldown` via `SendMessage("TakeDamage", damage)`. No-op
  when there is no Player; fully decoupled from AutopilotHealth (no code reference). Public fields
  moveSpeed/attackRange/attackCooldown/damage. Aliases düşman/enemy/mob/canavar. Pure ASCII, balanced.
  The combat trio (health + attack + enemy) is now in place. GAMES.md scripted row + doc guard. +7
  tests. **Next:** an `arena`/`brawler` blueprint — ground + WASD+attack player + health + N
  AutopilotEnemy enemies + score — as the 7th game type (cycle 54); arena NL intent + save/load/assess
  integration (cycle 55); later inventory/loot + xp/level.
- [x] Arena blueprint (cycle 54): `plan_arena_game(enemy_count, arena_size, seed)` — the **7th game
  type** and the first to wire the whole combat trio into a playable game. The player (tag Player) gets
  player + health + attack + score; N enemies (tag Enemy, placed in a ring) get the enemy AI + their own
  health — **mutual combat** (player's attack defaults to targetTag "Enemy"; the enemy AI targets the
  Player). The `attack` default targetTag was flipped "Player"->"Enemy" (its real use is the player's
  weapon), and `enemy` was added to `INTERACTIVE_BEHAVIOURS` so an arena (player + enemies, no goal)
  assesses as playable. Registered in BLUEPRINTS (7 games); seeded via the shared `_apply_seed` (enemy
  ring jitter); every seed validates + plays; variations work; a landing-doc row keeps the guard green.
  +10 tests. **Next:** arena NL intent ("arena / dövüş / brawler / savaş oyunu" + size + seed) +
  GAMES.md/catalog row (cycle 55); arena × save/load × variations integration + state review (cycle 56);
  later inventory/loot + xp/level.
- [x] Arena NL intent + docs (cycle 55): `detect_game_type` gained an arena branch
  (arena/dövüş/brawler/savaş/combat -> "arena") and `wants_game` learned arena/dövüş/brawler/"savaş
  oyunu"/"arena oyunu"/"dövüş oyunu", so "arena oyunu kur" / "build me a brawler" route to an arena
  build; size + seed work together ("arena oyunu kur 6 tohum 5" -> arena, size 6, seed 5). Crucially
  "savaş" does NOT collide with survival ("sağ kalma"/"hayatta kalma"), and the Unreal-only
  arena_survivor template is untouched (separate planner). GAMES.md §1 arena row + intent phrases + doc
  guard; the code-derived capability summary now reports "7 playable game types" and lists arena. The
  other six game intents are unchanged. +10 tests. **Next:** arena × save/load × variations × assess
  end-to-end integration + state review (cycle 56); then inventory/loot + xp/level.
- [x] Arena integration + `xp` behaviour (cycle 56): (a) end-to-end test — the arena combat game runs
  through the whole pipeline (NL intent "arena oyunu kur 4 tohum 9" -> plan -> serialize + disk
  save/load IDENTICAL; same seed rebuilds the same arena in another session; variations 2/4/6 all
  playable; assess playable+player; re-imported plan validates). (b) State review: P11 combat has the
  trio (health/attack/enemy) + the arena 7th game type + NL. Chose XP/leveling as the next building
  block (the defining action-RPG progression feature; same pure-template pattern as score/health; ties
  into arena via kill->XP). Shipped `xp` -> AutopilotXP MonoBehaviour: static XP/Level, `Add(int)` /
  SendMessage `AddXP(int)`, level-up at Level*100 XP (carrying the remainder), top-right "Lv N - XP"
  HUD. Aliases xp/seviye/level/tecrübe/deneyim. Pure ASCII, balanced; no NEEDS_SCRIPT behaviour
  un-templated. +12 tests. **Next:** wire `xp` into the arena (player carries xp; enemy death grants XP
  via SendMessage) (cycle 57); then inventory/loot; ranged/projectile attack.
- [x] XP wired into the arena via `reward` (cycle 57): new `reward` behaviour -> `AutopilotReward` — a
  killable enemy's HP + loot in one: it receives `TakeDamage`, and when HP runs out it grants `xpReward`
  to the Player (`SendMessage("AddXP")`, decoupled — no AutopilotXP reference) and destroys itself. The
  arena now gives the player `xp` (a Lv/XP HUD) and each enemy `enemy` + `reward` (instead of `health`,
  so the player's attack does single damage to one TakeDamage receiver). This CLOSES the combat loop:
  player attack -> reward.TakeDamage -> enemy dies + SendMessage AddXP -> player xp levels up; and enemy
  AI -> player health -> respawn. All fully decoupled SendMessage chains. Aliases ödül/reward/ganimet/
  xpdrop. Pure ASCII (fixed a stray em-dash), balanced, no NEEDS_SCRIPT behaviour un-templated; arena
  still valid/playable/deterministic. +8 tests (reward source/decoupled/ascii/aliases + the full
  combat-loop chain). **Next:** inventory/loot (kill -> item drop -> pick up) (cycle 58), or a state
  review on whether P11 is deep enough; ranged/projectile attack later.
- [x] Loot + inventory behaviours (cycle 58): two new scripted behaviours for an item economy. `loot`
  -> AutopilotLoot — a trigger pickup that, on Player touch, `SendMessage("AddItem", amount)` and
  destroys itself (decoupled — no inventory-type reference). `inventory` -> AutopilotInventory — a
  static item count with `Add(int)` helper + `AddItem(int)` SendMessage target + a top-left "Items: N"
  HUD (under the score). The pickup chain: loot touch -> AddItem -> inventory count. Aliases loot:
  item/eşya/loot/drop; inventory: envanter/inventory/çanta/items — "ganimet" deliberately stays with
  `reward` (no collision). Pure ASCII, balanced; no NEEDS_SCRIPT behaviour un-templated (7 action-RPG
  blocks now: health/attack/enemy/xp/reward/loot/inventory). GAMES.md rows + doc guard. +14 tests.
  **Next:** make a killed `reward` drop `loot` (kill -> item) and wire loot/inventory into the arena
  (cycle 59); state review on P11 depth (ranged attack? or P12) — choose then.
- [x] Loot in the arena + state review (cycle 59): the arena now gives the Player `inventory` (Items
  HUD) and scatters N `loot` spheres on the field to collect while fighting (a simple, decoupled item
  economy: walk over loot -> SendMessage AddItem -> inventory). Chosen scattered loot over a kill->drop
  spawn because it stays decoupled and testable (no reward->loot AddComponent coupling / runtime spawn);
  kill->drop is noted as a future refinement. Arena stays valid/playable/deterministic (9 unique scripts).
  **STATE REVIEW: P11 combat is comprehensive for a blocky prototype** — health, attack, enemy AI,
  xp/leveling, reward (kill->XP), loot, inventory, and the arena game wiring them all into a working loop
  (armed player vs enemies, kill->XP->level, collect loot->items). This honestly delivers the
  action-RPG-FLAVORED prototype promised when the user asked about KO/V Rising/Remnant 2/Valheim — a real
  game at that scale stays out of scope, but the mechanics work. +1 test. **Next:** one combat capstone —
  a `ranged` attack (projectile/raycast) to round out melee+ranged (cycle 60) — then P11 is done and the
  next big goal (P12) broadens beyond combat (candidates: a level/wave campaign, title/menu UI, audio
  cues, or spreading combat into other game types).
- [x] Ranged attack capstone (cycle 60): `ranged` -> AutopilotRanged — a long-reach attack (gun/bow):
  every `cooldown` it Physics.OverlapSpheres a large `range`, picks the NEAREST object tagged `targetTag`,
  aims at it (transform.forward) and damages it via `SendMessage("TakeDamage")` (decoupled). Differs from
  melee `attack` by reach (12 vs 1.5) and single-nearest targeting. Aliases menzilli/nisan/ates/ranged/
  shoot/mermi. Pure ASCII, balanced; no NEEDS_SCRIPT behaviour un-templated. GAMES.md row + doc guard.
  +10 tests. **P11 (combat) is DONE.** **Next:** state review + pick P12 beyond combat (cycle 61) —
  candidates: a level/wave campaign, a title/menu UI, audio cues, or spreading combat into other types.

### P12 — Waves & horde mode (survival-brawler depth)
**Cycle-61 state review.** P0–P11 done: 7 game types, persistence (save/load/import), procedural seeds,
and the full action-RPG combat set + arena. Tests 84 → 808. Chose **waves / horde mode** as P12 — it
turns the arena into a real survival-brawler (action-RPG "horde" endgame), reuses the existing combat
trio (enemy + reward), and is the most natural deepening of what's there. Picked over audio (polish,
not depth), title/menu UI (polish), spreading combat to other types (incremental), and procedural
terrain (a big separate effort).

- [x] Horde / wave behaviour (cycle 61): `horde` -> AutopilotHorde — a survival-brawler driver that
  spawns ESCALATING waves of enemies: every `waveInterval` it spawns `baseCount + (wave-1)*waveGrowth`
  enemy cubes (tagged Enemy, with `AddComponent<AutopilotEnemy>` + `AddComponent<AutopilotReward>`) in a
  ring, up to `maxWaves`. Deterministic ring placement (Mathf, no RNG). It necessarily AddComponents
  AutopilotEnemy/Reward (a spawner can't be type-decoupled), so it ships in a combat game that has them.
  Named `horde` (key + aliases akın/dalgalar/sürüsel) to avoid the existing `wave`/`dalga`->`spawner`
  aliases (verified unchanged). Pure ASCII, balanced; no NEEDS_SCRIPT behaviour un-templated. GAMES.md
  row + doc guard. +7 tests. **Next:** a horde/`arena` survival mode — an arena variant driven by the
  horde spawner instead of a fixed enemy ring (cycle 62); NL intent + integration (cycle 63).
- [x] Horde blueprint (cycle 62): `plan_horde_game` — the **8th game type**, a survival-brawler. The
  player (tag Player) gets the full combat kit (player + health + attack + ranged + score + xp +
  inventory); a central `Spawner` object runs the `horde` behaviour (escalating enemy waves); and one
  initial enemy (Enemy tag + enemy + reward) starts the arena populated AND ensures AutopilotEnemy.cs +
  AutopilotReward.cs are imported in the same recompile so the horde spawner (which AddComponents them)
  compiles; `enemy_count` scatters that many `loot` pickups. Registered in BLUEPRINTS (8 games); `horde`
  added to INTERACTIVE_BEHAVIOURS; seeded via _apply_seed (loot jitter); every seed validates + plays;
  variations work; landing-doc row keeps the guard green. The code-derived capability summary now reports
  8 game types automatically. +10 tests. **Next:** horde NL intent ("horde / survival brawler / dalga
  modu / akın oyunu" + size + seed) + GAMES.md/catalog row (cycle 63); state review (cycle 64).
- [x] Horde NL intent + docs (cycle 63): `detect_game_type` gained a horde branch
  (horde/dalga modu/akın/survival brawler -> "horde") placed BEFORE the survival branch, so "survival
  brawler" routes to horde while plain "sağ kalma"/"hayatta kalma"/"survival" still route to survival
  (the key disambiguation, tested). `wants_game` learned horde/"akın oyunu"/"dalga modu"/"horde oyunu"/
  "survival brawler"; size+seed work ("horde oyunu kur 6 tohum 5" -> horde, size 6, seed 5). assess +
  variations recognise horde. GAMES.md §1 row + intent phrases (doc guard asserts horde); the capability
  summary reports 8 game types and lists horde. The other seven game intents are unchanged. +10 tests.
  **Next:** horde × save/load × variations integration + state review on P12 direction (cycle 64) —
  title/menu UI, audio cues, or another direction.
- [x] Horde integration (cycle 64): a full-pipeline test — the horde game runs through NL intent ->
  serialize + disk save/load IDENTICAL; same seed rebuilds the same horde; variations 2/4/6 all playable;
  assess playable+player; re-imported plan validates. **P12 (horde mode) is DONE.** +5 tests.

### P13 — Game feel: win/lose state, then title/menu & audio
**Cycle-64 state review.** The studio has 8 game types + persistence + procedural + full combat/horde —
but the games never END. P13 adds game *feel*: a win/lose state + end screen (chosen over title/menu and
audio first, because an ending is the missing piece that makes every game a real game, and it is a pure
template that applies to all types). Title/menu UI and audio cues follow.

- [x] Win/lose state (cycle 64): `gameover` -> AutopilotGameOver — a win/lose manager + end screen.
  WIN once no objects tagged `Enemy` remain (after at least one existed); LOSE when something
  `SendMessage("PlayerDied")`s to it. It pauses (Time.timeScale=0), draws a centered "YOU WIN" /
  "GAME OVER", and reloads the scene on R. Static `IsOver`/`Won`. Aliases gameover/oyunsonu/sonekran/
  winlose/kazankaybet (chosen to avoid the existing `win`/`bitiş`->`goal` aliases, verified unchanged).
  Pure ASCII, balanced; no NEEDS_SCRIPT behaviour un-templated. GAMES.md row + doc guard. +8 tests.
  **Next:** wire `gameover` into the combat games (arena/horde manager object; player health death ->
  SendMessage PlayerDied) (cycle 65); then title/menu UI + audio.
- [x] Win/lose wired into combat games (cycle 65): the arena and horde blueprints now add a hidden
  `GameManager` cube (at y=-10) running the `gameover` behaviour, so the game ENDS — WIN when all
  Enemy-tagged objects are cleared, LOSE when the player dies. The lose path is decoupled: the player's
  `health` Die() now does `GameObject.Find("GameManager")?.SendMessage("PlayerDied", DontRequireReceiver)`
  before respawning (finds the manager by NAME, no type reference; a no-op in games without a manager,
  which is all the non-combat games — their players have no health anyway). Existing health behaviour
  (TakeDamage/Heal/respawn/HUD) is unchanged. arena/horde stay valid/playable/deterministic (arena now
  10 unique scripts, horde 12). +5 tests (arena/horde GameManager, health-signals-PlayerDied, updated
  unique-script counts). **Next:** title/menu UI behaviour (AutopilotTitle: title + "Press Space to
  start") + integration (cycle 66); audio cues; state review (cycle 67).
- [x] Title / start screen (cycle 66): `title` -> AutopilotTitle — a start screen. Draws `titleText`
  (default "GAME") + "Press SPACE to start" centered via OnGUI, holds the game **paused** until Space,
  then resumes (timeScale=1) and hides itself. Aliases title/başlık/menu/anaekran/başlangıç/startscreen.
  **timeScale conflict resolved:** gameover sets `Time.timeScale = 1` in its *Awake* (un-pause after an
  R-restart); a naive title would set 0 in Awake and race it (Unity's Awake order across objects is
  undefined). Fix: title sets `timeScale = 0` in **Start**, not Awake — Unity runs *every* Awake before
  *any* Start, so the title's Start always runs after gameover's Awake and the game reliably begins on
  the title screen, paused. Both behaviours are fully decoupled (no shared type). Pure ASCII, balanced,
  generate-only. title row added to GAME_STUDIO_GAMES.md scripted table + doc-guard generate list.
  +12 tests (source/timeScale-in-Start/hide-after-start/ascii/aliases/registered/no-collision-with-gameover).
  Kept behaviour-only this cycle (not wired into a blueprint) to avoid retest churn — wiring is a tiny
  follow-up. **Next:** state review (cycle 67) — P13 game-feel now has win/lose + title; decide audio
  cues vs. declaring P13 done and picking the next big goal (all-capabilities studio report / new type).
- [x] **State review + title wired into the flagship games (cycle 67).** Verdict: the `title` behaviour
  from cycle 66 was an orphan (no game used it), so the highest-value move was the "tiny follow-up" —
  wire it in. Both `plan_arena_game` and `plan_horde_game` now add `title` to their hidden GameManager
  alongside `gameover`, so the manager **bookends** the game: TITLE (start screen, paused) -> PLAY ->
  WIN/LOSE -> R restarts. Position-independent (screen-space OnGUI + global timeScale + Input), so the
  y=-10 hidden cube is fine for both. This exercises last cycle's Awake/Start ordering fix in a real
  game: gameover.Awake (timeScale=1) runs before title.Start (timeScale=0), so the game reliably starts
  paused on the title screen. arena now 11 unique scripts, horde 13. Both stay valid/playable/
  deterministic. Tests updated (manager bookend = {title, gameover}, arena 11-unique). 879 passed.
  - **Audio — honestly deferred, not faked.** P13 originally listed audio cues. But this studio is
    generate-only (it never imports real assets), and a sound cue needs an AudioClip. Rather than
    generate code referencing a fake/missing clip, the honest path (for a future cycle) is a procedural
    `AutopilotSound` that builds its clip at runtime via `AudioClip.Create` + a deterministic sine
    waveform (no external asset, no Math.random) and plays it on a decoupled `SendMessage("PlayCue")`.
    Deferred deliberately — recorded here so it isn't lost. **P13 game-feel is otherwise complete:
    win/lose + title, both wired into real games.**
  - **Next big goal (P14, cycle 68+):** with the per-game-feel loop complete, broaden the studio.
    Candidates: a procedural `AutopilotSound` (above), a fresh game type, or a consolidated
    "studio capabilities" report/landing refresh that reflects all 8 types + the full feel loop.
- [x] **Audio cue — done honestly (cycle 68).** Added `sound` -> AutopilotSound. The studio is
  generate-only (it never imports real assets), so faking an AudioClip / `Resources.Load("clip")` would
  be a lie. Instead AutopilotSound **builds its clip at runtime**: `AudioClip.Create` + `SetData` filled
  with a **deterministic** `Mathf.Sin` sine wave (frequency * 2*PI * t, with a short linear fade-out so
  it doesn't click) — no external asset, no `Math.random`, fully reproducible. Decoupled: `PlayCue()` /
  `PlayCue(float freq)` fire via `SendMessage("PlayCue", DontRequireReceiver)`, so any behaviour can
  trigger a cue without a hard type reference. Aliases sound/ses/audio/beep/sfx/sescue. Pure ASCII,
  balanced, generate-only. sound row added to GAME_STUDIO_GAMES.md + doc-guard list. +12 tests
  (procedural-not-fake / decoupled / deterministic / ascii / aliases / registered). 891 passed.
  Kept behaviour-only this cycle (wiring into a game is a small follow-up). **This closes P13's audio
  item honestly — P13 game-feel is fully complete: win/lose + title + sound.**

- [x] **Runner polished to a full-feel game (cycle 71).** Brought the P13 feel loop into a non-combat
  game. `plan_runner_game` now (a) adds a `sound` cue to the player and a hidden `GameManager` running
  `title`, so the run **begins paused on a title screen** (Space starts) and (b) the `killzone` template
  now `other.SendMessage("PlayCue", 200f, DontRequireReceiver)` on a hit — so hitting an obstacle
  **beeps** (the player carries a sound) before snapping back to start. The killzone change is decoupled
  and a no-op for every other game (dodge/chase/arena players have no sound) — all verified still
  valid/playable/deterministic. +2 tests (title-screen, killzone-hit-cue), updated player-set test.
  938 passed. The runner now has title -> auto-run + score -> hit = sound + restart.

### P14 — Broaden the studio (next)
With the full per-game feel loop done (title -> play -> win/lose, + a procedural sound cue), the next
arc widens coverage rather than depth. Candidates, pick highest-value per cycle:
- [x] Wire `sound` cues into the games decoupled (cycle 69). Both `plan_arena_game` and
  `plan_horde_game` now add `sound` to the hidden GameManager, so it runs title + gameover + sound.
  The `gameover` template now `SendMessage("PlayCue", freq, DontRequireReceiver)` **once on each
  transition** — 880f on win (after IsOver flips), 160f on lose (PlayerDied, now guarded with
  `if (IsOver) return;` so it can't re-fire). Fully decoupled: no hard type ref, a no-op when no
  AutopilotSound is present (all the non-combat games). arena now 12 unique scripts, horde 14; both
  stay valid/playable/deterministic. The end of a combat game now has audio feedback. +1 test
  (gameover-fires-sound), updated manager-set + unique-count tests. 892 passed. `sound` is no longer
  an orphan — it mirrors how `title` got wired in cycle 67.
- [x] A fresh **game type** — the **endless runner** (9th blueprint, cycle 70). The first type that
  ISN'T arena/collectathon-style, so it's a real variety addition. New `runner` behaviour
  (AutopilotRunner): auto-runs the player FORWARD (+Z), A/D strafe, Space jump (gravity arc, no
  Rigidbody), and feeds its own distance score via a decoupled `SendMessage("AddScore", 1)` each
  second (no-op without a score HUD). `plan_runner_game` lays a weaving lane of `killzone` obstacles
  (each snaps the player to the start on touch) — endless, so no goal/gameover. `_apply_seed` now also
  shifts `Obstacle_` lanes laterally (forward spacing kept), so seeds vary the weave. Intent:
  `detect_game_type` returns runner for runner/endless/koşu/koşma/sonsuz koşu (distinct terms, can't
  shadow others — "koşma" is NOT read as dodge's "kaçma"). Brittle exact-count tests loosened
  (`len(BLUEPRINTS) >= 8`, capabilities count is now code-derived). +43 tests. 935 passed.
- [x] A consolidated **code-derived "studio report"** (cycle 72). `build_studio_report()` in game_qa
  produces a comprehensive markdown report computed entirely from the live registries (BLUEPRINTS, the
  scripted-template + physics behaviour catalogs, the tool registry): all 9 game types + summaries, the
  behaviour catalog by category (27 scripted MonoBehaviours in control/movement/world/combat/progression/
  game-feel + 6 physics primitives), which games wire in title/win-lose/sound, persistence, procedural/
  seeded determinism, and the live tool count. Exposed as the `unity_studio_report` tool + the "studio
  raporu / yeteneklerin / capabilities / what can you do" NL intent (kept distinct from the lighter
  game-catalog intent, which still answers "neler yapabilirsin / what games"). A `_BEHAVIOUR_CATEGORIES`
  drift guard test asserts every unique MonoBehaviour class is categorized exactly once, so adding a
  behaviour forces it into the report. +14 tests. 952 passed. The studio can now describe itself
  accurately and on demand.
- [x] **Tower-defense -- the 10th game type (cycle 73)**, built ENTIRELY from existing blocks (no new
  behaviour). The trick that makes the combat parts act like a TD: the enemies' target is a stationary
  **Base** tagged Player + `health` -- the existing enemy AI (`FindWithTag("Player")`) marches to it,
  and when it falls it SendMessages PlayerDied -> gameover **LOSE**. Defending it: a line of `ranged`
  towers (already auto-target the nearest Enemy) + a mobile **hero** carrying the `player` controller
  (so the scene assesses playable) who is deliberately NOT tagged Player, so enemies head for the base,
  not the hero. **WIN** clears all enemies. `plan_tower_defense_game` registered as `tower_defense`
  (10th in BLUEPRINTS); intent routes "tower defense / tower-defense / kule savunma / td" (distinct
  phrases, can't steal other types). The code-derived studio report + capabilities auto-grew to 10
  types (drift guard green; no new behaviour, no new category). +33 tests. 985 passed.
- [x] **`timer` mechanic + time_survival -- the 11th game type (cycle 74).** First new MECHANIC since
  the feel loop: `timer` (AutopilotTimer) counts a `duration` down, draws the remaining seconds, and on
  zero fires a decoupled `SendMessage("Survived")` (freezes while paused, since it reads Time.deltaTime).
  `gameover` gains a `Survived()` WIN hook (mirrors PlayerDied but Won=true), so an "outlast the clock"
  game is won by surviving -- the existing enemy-clear WIN and PlayerDied LOSE still work, Survived is a
  third end path. `plan_time_survival_game` (11th type): armed player vs N enemies + a GameManager
  running title+gameover+sound+timer; WIN by surviving the countdown (or clearing enemies), LOSE on
  death. Distinct from `survival` (which never ends). Intent routes time-specific phrases ("zamana
  karsi / sureli hayatta kalma / survive the clock") BEFORE survival, so plain "hayatta kal / survival"
  still routes to survival. timer added to `_BEHAVIOUR_CATEGORIES` (game feel) so the report drift guard
  stays green; report auto-grew to 11 types. Caught + avoided an alias collision (`sayac` stays score).
  +40 tests. 1025 passed (crossed 1000).
- [x] **Freeform game composer (cycle 75)** -- the biggest step from "pick a preset" to "assemble what
  you described." `compose_custom_game(player, enemy, collectible, hazard, goal, timer)` builds a valid,
  playable plan from the same building blocks, wiring the sensible couplings automatically: enemies ->
  the player gains health+attack and a win/lose GameManager appears; collectibles/enemies -> a score
  HUD; a timer -> an outlast-the-clock manager; plus optional hazards (killzone) and a goal zone. Counts
  clamp to [0,30]; a player-only request is an honest sandbox (assesses not playable). `parse_custom_spec`
  turns a freeform description ("5 dusman, 3 toplanabilir ve bir sayac") into those kwargs (digits +
  TR/EN number words + bare-word=1). Exposed as `unity_compose_game` (execute-free by default) + an
  intent gated on explicit "ozel / custom / kendi / karisik oyun" framing, checked BEFORE the preset
  build intent so it can NEVER steal a blueprint ("toplama oyunu" still builds a collectathon -- verified).
  The studio report gained a code-derived "Custom composition" section. +17 tests. 1042 passed.
- [x] **Composer enriched (cycle 76).** Two upgrades, both keeping every preset safe: (1) **keyword-less
  routing** -- a freeform element list now reaches the composer WITHOUT the "ozel/custom" keyword
  ("5 dusman 3 toplanabilir oyun yap" -> compose). The gate is tight: a build verb + parse_custom_spec
  finds >=1 element + `detect_game_type()=="collectathon"` (no preset matched) + no "toplama/collectathon"
  keyword -- so "toplama oyunu" still builds a collectathon, a bare "oyun yap" (no elements) still
  defaults, and arena/dodge/horde/maze/tower_defense/runner/time_survival all still win. (2) **seed** --
  `compose_custom_game(..., seed=...)` reuses `_apply_seed` to jitter the placed-element layout
  deterministically (seed=None is the plain plan); the intent extracts "tohum 7" via extract_seed and
  passes it through. +6 tests (keyword-less routing, broad preset-protection, seed determinism). 1048
  passed.
- [x] **Design critique -- the studio reviews its own output (cycle 77).** State-review pick: an HONEST
  design linter, `critique_design(behaviour_counts)`, derived purely from the plan's counts (no faked
  simulation). It flags coherence/balance gaps a structurally-"playable" game can still have: enemies but
  nothing with health (no lose condition), enemies but no player attack (one-sided), an attack/ranged
  with no enemies to hit, a win/lose manager with no WIN trigger (no enemies + no timer), a countdown with
  no combat lose path. Surfaced as `design_notes` in `assess_game_readiness` (and so in
  `unity_assess_game`). All 11 shipped blueprints produce ZERO notes (no false positives -- a regression
  guard for future blueprints), while incoherent composer specs (e.g. player+timer, no enemies) get an
  honest note. +21 tests. 1069 passed. The studio can now critique a game, not just pass/fail it.
- [x] **Composer element richness (cycle 78).** Two new optional elements on `compose_custom_game`,
  reusing existing behaviours: `spawner` (int, clamped [0,20]) -> elevated wave spawners that rain
  hazards (survival-style, playable on their own), and `ranged` (bool) -> the player also gets a `ranged`
  weapon (auto-hits the nearest enemy). `parse_custom_spec` learns them (spawner/uretici/dalga/wave;
  menzilli/nisan/ranged/tufek) and the keyword-less gate counts them as elements. The design critique
  stays coherent across the new combos -- "ranged with no enemies" is flagged, spawner-only is clean and
  playable, ranged+enemies is clean. Seed determinism extends to the new elements. Verified the spawner
  words can't steal the horde preset ("dalga modu" -> horde). +7 tests. 1076 passed.
- [x] **Composer + persistence (cycle 79)** -- the composer story end to end: describe -> keep -> reload
  -> build. Verified a composed plan (game='custom', with its spec) already round-trips through game_io
  cleanly (serialize/deserialize/validate/assess; steps + spec preserved). Added `unity_save_composed_game`
  (composes the element mix + writes it under the saved-games dir, path-traversal-guarded) and a
  composed-save sub-branch in the save intent: a freeform "ozel oyunu X olarak kaydet" / "5 dusman 3
  toplanabilir oyununu boss olarak kaydet" saves the COMPOSED plan, gated exactly like the composer
  intent so "dodge oyununu kaydet" still saves a dodge and "kaydet boss" still saves a collectathon.
  Loading is already generic (a custom plan is just a plan) -- verified a loaded custom game validates +
  assesses playable + is buildable. +11 tests. 1087 passed. (Known minor limitation: a save NAME that
  itself contains a preset keyword, e.g. "arena2", is read as that preset by detect_game_type -- ordinary
  names are unaffected.)
- [x] **Multi-level campaigns (cycle 80, milestone state review).** Health check first (1087 green,
  import OK), then a new STRUCTURAL axis: `plan_campaign(game_type, levels, seed)` builds an ordered,
  increasing-difficulty sequence (element count climbs 2,4,6,...) of N FULL playable levels -- each with
  a difficulty label, a readiness check (design_notes too), and its complete plan, so levels can be
  built or saved (unlike `plan_game_variations`, which returns only summaries). An optional seed gives
  each level a distinct reproducible per-level seed. `unity_plan_campaign` returns a lean glanceable
  view (drops the full step plans). Intent: "X kampanyasi / 3 seviyeli X / campaign" -> a campaign,
  checked before the build/composer intents so "arena kampanyasi" plans a campaign while "arena oyunu
  kur" still builds one and "arena varyasyonlari" still lists variations. Works for all 11 blueprints
  (parametrized test). +22 tests. 1109 passed. The studio can now plan a progression, not just one game.
- [x] **Stealth -- the 12th game type, the first won by AVOIDING combat (cycle 81).** New `detector`
  behaviour (AutopilotDetector: each frame finds the Player; within `sightRange` it SendMessages
  "PlayerDied" to the GameManager -> caught/LOSE; decoupled, by name, fires once). A third gameover WIN
  hook `ReachedGoal()` (mirrors Survived), and the `goal` zone now also SendMessages "ReachedGoal" to a
  GameManager on entry (decoupled, no-op without one -- the other goal-using games are unaffected).
  `plan_stealth_game` (12th type): player + a goal exit + N patrolling guards (`patrol` + `detector`),
  deliberately NOT tagged Enemy so the clear-all-enemies WIN can't mis-fire -- the only win is reaching
  the exit. The design critique was updated so a goal counts as a WIN trigger (gameover + goal + no
  enemy/timer is now coherent, not "can only be lost"); all 12 blueprints stay clean. Intent routes
  stealth/gizlilik/gizli gec/sneak. Docs (Eleven->Twelve + rows), drift/ASCII guards green; report
  auto-grew to 12. +41 tests. 1150 passed.
- [x] **Campaign + persistence (cycle 82, state review).** Health check first, then completed the
  campaign story (parallel to cycle 79's composer+persistence). `unity_save_campaign(game_type, levels,
  name, seed)` plans an increasing-difficulty campaign and writes each level as `<name>_L1.json ..
  <name>_LN.json` (path-traversal-guarded via the existing save_plan_to_file), so the whole progression
  can be reloaded and built level by level. A campaign-save sub-branch in the save intent routes "X
  kampanyasini Y olarak kaydet" / "3 seviyeli arena kampanyasini kaydet" there, checked FIRST in the
  save branch so a plain preset save ("dodge oyununu kaydet"), a composed save ("ozel oyunu X kaydet"),
  and a campaign PLAN ("arena kampanyasi kur", no "kaydet") are all unaffected. +6 tests. 1156 passed.
  The studio can now keep a whole progression, not just one game.
- [x] **Composer gains stealth guards (cycle 83)** -- the newest game type wired into the freeform
  composer. `compose_custom_game(..., guard=N)` places N patrolling `Capsule` guards (`patrol` +
  `detector` line-of-sight, NOT tagged Enemy, so they can't be cleared -- you slip past them).
  Coherent couplings, mirroring `enemy -> health+attack`: any guard creates the win/lose GameManager,
  and guards imply a goal to reach (auto-added if the user didn't ask for one) so there IS a way to win
  -- the design critique then stays clean. `parse_custom_spec` learns guard/muhafiz/nobetci/koruma/bekci;
  the keyword-less gate + composed-save both count guards. Seed determinism extends to the guard
  placement. "3 muhafiz olan oyun yap" composes a stealth-style custom game; the stealth PRESET keywords
  ("gizli gec / stealth") still build the blueprint (no theft). +6 tests. 1202 passed.
- [x] **Multi-agent role models (cycle 84)** -- the dual-agent roles now each use the model that fits
  their job (completes the cycle-83 model-router work). `model_for_role()` in the router: Master ->
  reasoning (`gpt-oss-120b`), Worker -> a tool-capable general model (`llama-3.3-70b`), Reader -> fast
  (`llama-3.1-8b-fast`). `DualAgentOrchestrator._clone_config(role=...)` sets each role's
  `cloudflare_model` from the router AND turns off per-message auto-routing inside the role, so a role's
  assigned model is authoritative. Ollama mode and no-role/non-cloudflare clones are untouched; the
  Worker's model is always tool-capable so its tool-loop works. +4 tests. 1206 passed.
- [x] **Self-criticism everywhere (cycle 85)** -- the design critique is now consistent across all the
  studio's reporting surfaces. New `studio_health()` in game_qa: a code-derived self-audit that builds
  every blueprint and checks it is VALID (whitelisted tools, no traversal), PLAYABLE, and COHERENT (no
  design-critique notes), returning a per-game verdict + a `flagged` list (empty when all clean). The
  studio report gained a "Studio health: OK (N/N)" section (or a flagged list if something regresses --
  a built-in self-test of the whole catalog). `plan_game_variations` now also carries `design_notes` on
  each variation, so difficulty options get the same self-review as a single build. All 12 game types
  audit clean. +14 tests. The studio reviews not just one game but its entire output, everywhere.
- [x] **Puzzle / sokoban -- the 13th game type (cycle 86)**, the first with a PUSH mechanic and no
  combat/timer. Two new behaviours: `pushable` (AutopilotPushable -- a crate slides AWAY from the
  approaching Player; decoupled by tag, deterministic, no physics tuning) and `puzzle` (AutopilotPuzzle
  -- a win manager that finds `Crate_*`/`Target_*` **by name**, so NO custom Unity tags and NO hard type
  references are needed, draws "Crates: covered/total", and WINS once every target has a crate on it).
  `plan_puzzle_game`: a WASD player + N pushable crates + N target markers (open arena, so always
  solvable) + a GameManager running puzzle+title+sound. `pushable` added to INTERACTIVE_BEHAVIOURS so the
  puzzle assesses playable; both behaviours categorised in the report drift guard. Intent routes
  puzzle/sokoban/bulmaca/kutu-itme (no theft). studio_health now audits 13/13 valid+playable+coherent.
  Docs Twelve->Thirteen + rows. +40 tests. 1260 passed.
- [x] **Self-audit exposed as a tool (cycle 87).** `studio_health()` was only inside the report; now it's
  directly queryable. New `unity_studio_health` tool returns the full self-audit (every game type valid +
  playable + coherent, with a `flagged` list), and an NL intent routes "studio sagligi / saglik denetimi
  / studio health / her sey yolunda mi / oyunlar saglikli mi" to it -- checked before and kept distinct
  from the studio-report intent ("studio raporu" still -> the descriptive report). +2 tests. 1262 passed.
- [x] **Composer gains sokoban crates (cycle 88)** -- the newest mechanic (puzzle) wired into the
  freeform composer, mirroring the cycle-83 guards. `compose_custom_game(..., crate=N)` places N
  `pushable` crates + N `Target_*` markers and adds the `puzzle` win-manager to the GameManager (push
  every crate onto a target). Coupling is clean: the manager runs `gameover` for enemy/guard/timer
  and/or `puzzle` for crates (both can coexist). `parse_custom_spec` learns kutu/crate/sandik/kasa.
  Intent collision resolved carefully: "crate" is no longer a puzzle-preset trigger on its own, so a
  freeform "3 kutu olan oyun" composes while the push phrasing ("kutu itme") and sokoban/bulmaca/puzzle
  still build the PRESET (verified both ways). +5 tests. 1267 passed.
- [x] **Composer report -- the 4th self-awareness surface (cycle 89).** The composer now has 10 element
  types; `build_composer_report()` makes them discoverable: a CODE-DERIVED markdown guide listing each
  counted element (enemy/collectible/hazard/spawner/guard/crate) and flag (goal/timer/ranged) with its
  trigger words -- read straight from the live `_SPEC_ELEMENT_WORDS`/`_SPEC_FLAG_WORDS` so it can't drift
  -- plus the automatic couplings (curated prose, guarded by a test that every coupling names a real
  spec key). Exposed as `unity_composer_report` + an intent ("composer raporu / ne tarif edebilirim /
  what can i compose / hangi ogeler") kept distinct from the studio-report, health, and catalog intents.
  The studio can now describe itself four ways: capabilities, models, health, and the composer. +3
  tests. 1270 passed.
- [x] **King of the hill -- the 14th game type (cycle 90, milestone)**, a genuinely new mechanic: won by
  HOLDING a position (not fighting / reaching / avoiding). New `holdzone` behaviour (AutopilotHoldZone):
  while the Player is within `radius` a meter fills, and at `holdTime` it SendMessages "Survived" to the
  GameManager -- reusing gameover's existing WIN hook, no new manager code. `plan_hold_game`: a player
  with movement + `health` but NO attack + a central hold zone + N enemies (chase + attack to shove you
  out). WIN by holding; LOSE by dying; since the player can't attack, clearing enemies is not a win path.
  The design critique was refined: the "no attack -> one-sided" note now only fires when there is NO
  non-combat win path (a `goal` or `holdzone` makes avoiding the enemies the intended play) -- it still
  flags genuinely one-sided fights. holdzone added to INTERACTIVE_BEHAVIOURS + the report category.
  studio_health audits 14/14 valid+playable+coherent. Intent routes "king of the hill / bolge tut /
  hold the zone / zone control" (no theft). Docs Thirteen->Fourteen. +40 tests. 1310 passed.
- [x] **Composer self-audit (cycle 91).** The self-audit now covers the composer too, not just the
  blueprints. New `compose_health()` composes a representative matrix of element specs (each type alone +
  a few mixes: enemy/collectible/hazard/spawner/guard/crate, enemy+timer, enemy+collectible+ranged, a
  mixed enemy+crate+guard) and checks each is valid + playable + coherent -- a regression guard for the
  composer couplings (enemy -> health+attack, guard -> goal, crate -> puzzle, ...). The studio report's
  health section now reads "OK (14/14 game types, 10/10 composer cases)" and `unity_studio_health`
  returns a nested `{blueprints, composer, all_ok}` (its two report tests updated for the richer shape).
  All 10 composer cases audit clean. +1 test. 1311 passed.
- [x] **Campaign self-audit (cycle 92).** The self-audit now covers campaigns too -- the last surface it
  didn't reach. `plan_campaign` now `validate_plan`s each level (previously only `playable` +
  `design_notes` were checked, so whitelisted-tools / no-traversal wasn't verified per level) and adds a
  per-level `valid` plus per-campaign aggregate `all_valid` / `all_playable` / `all_coherent` flags --
  the same shape `studio_health` uses, so a whole progression self-reports its health. The
  `unity_plan_campaign` lean view carries the new flags automatically (it only drops each level's full
  plan). Every game type's campaign audits clean. +16 tests. 1327 passed. The studio now audits all
  four of its output shapes: blueprints, composer, and campaigns (single games via assess).
- [x] **Escort / VIP -- the 15th game type (cycle 93).** A new mechanic: protect a thing that ISN'T you.
  New `escort` behaviour (AutopilotEscort) -- a VIP that walks ITSELF toward a named goal (MoveTowards,
  deterministic) and fires a one-time "ReachedGoal" on arrival (reusing gameover's WIN hook, no gameover
  change). `plan_escort_game` is the tower-defense inversion with a MOVING base: the Escort is tagged
  Player (so the existing enemy AI marches at the thing you protect) + `health` (destroyed -> LOSE); a
  separate, untagged Hero is the controllable bodyguard (player + attack + score) who clears the N enemies
  before they reach the VIP. Deliver the VIP (ReachedGoal) -- or clear every enemy -- to WIN. Categorized
  under "world" (drift guard); studio_health + every campaign now audit 15/15 clean. Intent routes
  escort/refakat/vip/eskort, kept distinct from the guard-composer word "koruma" (no theft). Docs
  Fourteen->Fifteen + game/behaviour rows + NL lists. +38 tests. 1365 passed.
- [x] **Boss fight -- the 16th game type (cycle 94).** The first sustained single-target DUEL (one tough
  foe, not a swarm). New `boss` behaviour (AutopilotBoss) -- a single high-HP enemy that chases +
  melee-attacks the player, draws an on-screen boss HP bar, and on death grants big XP + DESTROYS itself
  so gameover's clear-all-enemies WIN fires. `plan_boss_game`: an armed player (health + melee attack +
  ranged so you can chip it at distance + score + xp) vs N bosses (tag Enemy). The design critique was
  taught a `boss` is a foe like `enemy` (`foes = enemy + boss`), so a boss-only duel is coherent (no false
  "attack with no enemies" / "no win trigger" flags) -- backward compatible with every enemy-based note.
  boss added to INTERACTIVE_BEHAVIOURS + the "combat" drift category. studio_health + every campaign now
  audit 16/16 clean. Intent routes on MULTI-WORD phrases only (boss fight / boss arena / patron savasi /
  ...) because a bare "boss" is a very common SAVE NAME -- so "boss olarak kaydet" / "kaydet boss" keep
  working untouched, and "boss arena" picks boss before the "arena" term. Docs Fifteen->Sixteen + rows.
  +38 tests. 1403 passed.
- [x] **Collector race -- the 17th game type (cycle 95).** The first type won by BEATING A DEADLINE (the
  clock is your enemy). New `collectrace` behaviour (AutopilotCollectRace) -- a manager that counts the
  remaining "Collectible_*" by name (decoupled, no tags) and SendMessages a one-time "ReachedGoal"
  (reusing gameover's WIN hook) when the last is gone, or "PlayerDied" (the LOSE -- the studio's first
  losing deadline) if its countdown reaches zero first. `plan_collector_race_game`: a WASD player + score
  + N collectibles + the manager (collectrace + gameover + title + sound). Distinct from `collectathon`
  (no clock) and `time_survival` (the timer is a WIN). The design critique learned a `collectrace` is a
  valid WIN trigger (so a gameover paired with it is coherent, not "can only be lost"); backward
  compatible. Categorized under "game feel" (drift guard). studio_health + every campaign now audit 17/17
  clean. Intent routes on MULTI-WORD phrases (collector race / toplama yarisi / sureli toplama / ...) so a
  bare "toplama" still builds a collectathon. Docs Sixteen->Seventeen + rows. +38 tests. 1441 passed.
- [x] **Game showcase -- a self-verifying discovery gallery (cycle 96).** A different KIND of value after
  three straight new types: a user-facing "say this -> get this game" gallery AND the first regression
  guard for the whole NL-intent layer per game type. New `_GAME_EXAMPLES` (a curated example prompt +
  pitch per game type), `showcase_routing()` (checks LIVE that each example routes to unity_build_simple_game
  for its own type), and `build_game_showcase()` (the markdown gallery: example + pitch + object count).
  A test asserts every BLUEPRINTS type has an example (drift guard) and every example builds its type, so
  breaking any game's detection turns the showcase red. Exposed as the `unity_game_showcase` tool + the
  "ornek oyunlar / show me examples / game examples" intent (placed before catalog + build so it isn't
  shadowed; verified it steals neither). The 5th self-awareness surface (after catalog, report, health,
  composer-report). All 17 examples verified to route. +29 tests. 1470 passed.
- [x] **Moving-hazard composer element (cycle 97).** Back to production after the showcase: the freeform
  composer gains an 11th element, a SLIDING obstacle (`mover` + `killzone`, the dodge game's threat). The
  interesting part is the parser -- the Turkish trigger "hareketli engel" (moving hazard) CONTAINS the
  static-hazard word "engel", so a new `_SPEC_PHRASE_ELEMENTS` is extracted + STRIPPED before the
  single-word elements (`_count_and_strip_phrase`): "2 engel ve 4 hareketli engel" parses to hazard=2 +
  moving_hazard=4, not a double-count. `compose_custom_game` gains a `moving_hazard` count (a pure
  obstacle -- no manager/health coupling, like the static hazard); the spec dict + composer report + both
  compose tools carry it; `compose_health` grew to 12 cases (a moving-hazard-only case + a mix), all
  clean. While here, fixed a latent gap: `unity_save_composed_game` now plumbs guard/crate/moving_hazard
  (it silently dropped guard/crate before). +15 tests. 1485 passed.

- [x] **Arena mini-boss -- depth for the 7th type (cycle 98).** After three new types, a showcase, and a
  composer element, this cycle adds DEPTH to an existing game instead of breadth. plan_arena_game now
  places a single high-HP MINI-BOSS across the arena (the existing `boss` behaviour -- NO new C#), tagged
  Enemy so the clear-all-enemies WIN includes it, drawing its own HP bar -- the climax you whittle down
  while the swarm pressures you. It is named "Boss" (not Enemy_*), so the enemy-swarm assertions are
  untouched and the ONLY existing arena test that changed is the unique-scripts count (twelve -> thirteen,
  +boss). Arena stays coherent (foes = enemy + boss, with player health + attack), so studio_health is
  still 17/17, the showcase still routes "arena oyunu kur" to arena, and the dedicated `boss` duel type
  stays distinct ("boss arena" still picks the boss type). +2 tests. 1487 passed.

- [x] **Integration hardening -- prove the chat -> Unity build path (cycle 99).** The studio was deeply
  unit-tested at the PLAN level but the actual EXECUTE path (turning a plan into live bridge calls) had
  ZERO automated coverage, and the live check (scripts/live_check.py) never built a game -- so "does it
  really work end to end" was unproven. Closed that honestly: (1) `tests/test_game_build_integration.py`
  drives `unity_build_simple_game(execute=True)` for ALL 17 game types + composed games against a recording
  fake bridge and asserts the real phase order (geometry -> import each UNIQUE script once -> poll
  get_editor_state -> attach a component per object); (2) `tests/test_bridge_protocol_parity.py` parses the
  C# command vocabulary out of `unity_plugin/Editor/Bridge/CommandHandlers.cs` and asserts EVERY RPC method
  the Python build path emits (create_primitive/set_tag/import_asset/get_editor_state/add_component/
  add_collider/get_object_details) is handled by the editor -- the exact drift that would silently break a
  live build now fails CI; (3) a full chat-loop test: the sentence "boss arena oyunu kur ve uygula" drives
  a real 39-call build through run_unity_fast_action, while plain "kur" makes ZERO bridge calls. Added an
  explicit BUILD opt-in to the fast path (multi-word "ve uygula" / "sahneye uygula" / "build and apply" ->
  execute=True + write=True; safe execute=False default preserved). Added `scripts/build_check.py` (the live
  counterpart to live_check.py -- snapshots then builds a real game) and `docs/INTEGRATION_STATUS.md`
  (what's wired, what's CI-proven, what needs a live editor + exact commands). +30 tests. 1517 passed.

- [x] **Turret composer element -- a 'run the gauntlet' threat (cycle 100).** Back to game-making after the
  integration cycle: the freeform composer gains a 12th element, a stationary RANGED threat. New `turret`
  behaviour (AutopilotTurret -- the mirror of the player's `ranged`): it does not move, finds the Player in
  range and damages it via SendMessage("TakeDamage") on a cooldown. In the composer it is NOT tagged Enemy
  (you cannot clear it), so it reuses the proven guard coupling: `turret > 0` -> the player gains `health`
  (so the fire can defeat you) + a goal is auto-added (the way to win) + a gameover manager -- i.e. dodge
  the turret fire to reach the exit. Coherent by the critique (a goal-win + health-lose game, no false
  flags); `turret` added to INTERACTIVE_BEHAVIOURS + the combat drift category; compose_health grew to 14
  cases, all clean (studio report now "14/14 composer cases"). Triggers "taret"/"turret" (distinct from
  tower_defense's "kule savunma" -- no theft), and the cycle-99 build opt-in works with it ("3 taret oyunu
  kur ve uygula" -> a real build). Both compose tools plumb it. +15 tests. 1532 passed.

- [x] **Hitflash -- the first feel/juice layer (cycle 101).** A different KIND of value: visual hit
  feedback. New `hitflash` behaviour (AutopilotHitFlash) -- on SendMessage("TakeDamage") the renderer
  flashes `flashColor` then lerps back over `flashTime`. Purely cosmetic + decoupled (runs alongside the
  real damage handler), deterministic (only Time, no RNG), a no-op without a Renderer. Wired onto BOSSES
  only (the `boss` type's bosses + the arena mini-boss) -- a design-correct choice: a flash only reads on a
  HIGH-HP, multi-hit target; the one-hit swarm (which dies instantly) would never show it, so it does not
  get the behaviour. Cosmetic, so it changes nothing in the critique/playability: studio_health stays
  17/17, both blueprints stay coherent. Low churn -- only the two Boss behaviour-set assertions changed
  (+ arena unique-scripts thirteen -> fourteen). Categorized under "game feel" (drift guard); doc behaviour
  row added. A reusable juice primitive future cycles can extend to other targets. +11 tests. 1543 passed.

- [x] **Maze dead-end traps -- depth, always-solvable by construction (cycle 102).** The maze gains stakes:
  a killzone in every DEAD-END cell, so a wrong turn respawns you. The safety is structural, not luck: in a
  perfect maze the dead-ends (leaves of the spanning tree) are GUARANTEED off the unique entrance->exit
  solution path, so the traps can never block it -- the maze stays always-solvable. New
  `core.maze.maze_dead_end_cells` (a cell with exactly one open passage, excluding entrance/exit; pure +
  deterministic from the seeded grid); plan_maze_game places a Trap_* killzone in each. Verified: traps
  never sit on the player cell, the goal cell, or a wall; every seed/size stays solvable; object_count
  stays bounded (size-8 = 174 < 200). One real test conflict surfaced + fixed honestly: the maze is the
  ONE blueprint whose seed changes the actual topology (not just a jitter), so its object count is now
  legitimately seed-DEPENDENT (different topologies have different dead-end counts) -- excluded it from the
  jitter-only seed-independent-object-count invariant + added a maze-specific bounded-count test (walls
  stay seed-independent). studio_health stays 17/17. +26 tests. 1569 passed.

- [x] **Twin-stick shooter -- the 18th game type (cycle 103).** The first RANGED-PRIMARY game, filling a
  recognizable genre gap. plan_twinstick_game: a lean KITER -- movement + `health` + a `ranged` auto-aim
  weapon + score, with NO melee attack, no xp/loot/inventory -- backs away from a ring of N enemies (enemy
  AI + reward, tag Enemy) while the gun mows them down. WIN by clearing the ring (gameover's enemy-clear),
  LOSE if cornered. No new C# -- reuses existing behaviours. Distinct from `arena` (melee brawler with
  xp/loot + a mini-boss) and `horde` (full kit + a wave spawner). Purely additive: new blueprint + registry
  + a _GAME_EXAMPLES showcase entry (verified to route) + intent on distinct phrases (twin stick / twinstick
  / top down shooter / iki yon ates) kept clear of the composer's `ranged` flag ("nisan/menzilli"), so a
  composed ranged game is not stolen. studio_health + showcase + the report all read 18/18; every
  twin_stick campaign audits clean. Coherent by the critique (ranged + enemies + gameover, no false flags).
  Docs Seventeen->Eighteen + rows + NL lists. +34 tests. 1603 passed.

- [x] **Game anatomy -- a single-game deep-dive (cycle 104).** A different KIND of value: the 6th
  self-awareness surface, but at SINGLE-game granularity (the others are catalog-wide). New
  `build_game_anatomy(game_type)` -- for one type it shows its size (object + unique-script counts),
  behaviours grouped by category (control/movement/world/combat/progression/game feel/physics), the build
  phases (geometry -> import each unique script ONCE -> attach), the playability verdict + any design
  notes, and the example prompt. All code-derived from plan_game + assess_game_readiness +
  group_execution_plan, so it never drifts (verified ASCII + numbers-match-the-plan for all 18 types).
  Exposed as `unity_game_anatomy(game_type)` + an intent keyed on anatomy/breakdown phrases ("X oyununun
  yapisi / X oyunu anatomisi / breakdown of X / X neyden olusuyor"). The intent uses `yapisi` as a
  token-PREFIX so a build's "yap"/"yapsana" never matches it (verified build/assess/showcase/catalog
  intents are all untouched). +46 tests. 1649 passed.

- [x] **Tower-defense wave spawner -- depth for the 10th type (cycle 105).** Tower-defense had only a
  FIXED enemy group -- the genre-defining ESCALATING WAVES were missing. plan_tower_defense_game now adds a
  `horde` wave spawner on the far enemy side (the existing behaviour -- NO new C#): it rains escalating
  waves of enemies (tagged Enemy, with the enemy AI + reward it AddComponents, already imported by the
  fixed group), and since the enemy AI targets FindWithTag("Player") = the Player-tagged Base, every wave
  marches at the base just like the fixed group. So it is now a real escalating defense, won by clearing
  every wave. Near-zero churn: the Spawner is a separate object (not Enemy_*, not the GameManager), so all
  existing tower_defense assertions hold untouched (Base/Hero/towers/manager unchanged, the fixed Enemy_*
  group intact, "only existing behaviours" still true since horde is one). studio_health stays 18/18, the
  td campaign + anatomy + showcase all stay clean. +1 test. 1650 passed.

- [x] **Pickup pop -- universal collect-moment juice (cycle 106).** A second feel layer, but UNIVERSAL and
  zero-churn: the existing `collectible` behaviour (AutopilotCollectible) now scores IMMEDIATELY on pickup
  then plays a short scale-up "pop" (Time-driven `popTime`/`popScale`) before destroying itself -- a grab
  finally feels good. It is a pure SOURCE enrichment: the behaviour name/class is unchanged, so every game
  that uses collectibles (collectathon / chase / collector_race + the composer) gets the juice for free
  with NO plan/structure change (verified the grouped script/attachment sets are identical and
  studio_health stays 18/18). A `collected` guard keeps scoring exactly once even during the pop;
  deterministic (only Time, no RNG); still fully decoupled (no AutopilotScore reference). All the existing
  collectible-source assertions (OnTriggerEnter / CompareTag / Destroy / isTrigger / SendMessage AddScore /
  no hard score ref) are preserved, so nothing broke -- only the C# got richer. +4 tests. 1654 passed.

- [x] **Platformer moving hazards -- depth for the 4th type (cycle 107).** The platformer was the weakest
  type: just climb a staircase to the goal, NO threat. Now every OTHER ledge (the odd-indexed platforms; the
  first is always safe) carries a moving HAZARD at player height -- a `patrol` (ping-pongs it along x, so it
  STAYS in play and sweeps across the ledge, unlike a one-direction mover) + a `killzone` (touch ->
  respawn). You must time your jump onto a guarded platform for when the hazard is at the far end -- real
  platformer danger, and never a hard block (it only respawns you, so it stays winnable). No new C# (reuses
  patrol + killzone). Low churn: the hazards are separate Hazard_* objects, so the staircase/goal/clamp/seed
  assertions hold untouched; only the unique-scripts test changed (two -> four, +patrol/killzone). The
  hazard count is fixed per platform_count (floor(n/2)), so the object count stays seed-INDEPENDENT (the
  seed still only jitters platform x). studio_health stays 18/18; coherent (killzone has no critique
  impact). +1 test. 1655 passed.

- [x] **Survival real objective + threat -- depth for the 3rd type (cycle 108).** Survival was the WEAKEST
  type: harmless physics-cube rain, NO threat, NO win. plan_survival_game now keeps the spawner rain (chaos
  + cover-blocking clutter) but adds N deadly `killzone` floor patches (touch -> respawn; a real threat) and
  a GOAL exit at the far side, with a hidden GameManager (title + gameover) -- brave the cluttered,
  hazard-strewn arena and reach the exit to WIN. It used to have neither a win nor a danger; now it has
  both, reusing only existing behaviours (NO new C#). Coherent by the critique (a goal-win game, foes=0,
  no timer -> no false flags); playable + has_goal now true. The hazard count is fixed per spawner_count,
  so the object count stays seed-INDEPENDENT, and variations stay ascending. studio_health stays 18/18.
  One legitimate test follow-on: test_game_qa's "a playable game can lack a goal" example moved off survival
  (it now HAS one) onto arena (which genuinely has no goal). Churn limited to the unique-scripts test.
  +1 test. 1656 passed.

- [x] **Game how-to -- a player-facing 'how to play' card (cycle 109).** The 7th self-awareness surface,
  and the first PLAYER-FACING one. New `game_howto_from_plan` derives, straight from a plan's behaviour
  counts, the controls (WASD/jump/auto-aim/auto-melee/push), how to win (reach the goal / clear enemies /
  hold the zone / push crates / collect before the clock / guide the VIP / outlast the timer / endless
  score), what to watch out for (the threats: enemies/boss/turrets/guards/hazards/spawners/waves), and how
  to lose (health out / spotted / time out). `build_game_howto(game_type)` renders the card. Because it
  reads only the behaviours, it works on ANY plan -- a preset OR a freeform COMPOSED game (where there is NO
  hand-written description), which is the real value: a how-to for a game nobody wrote a summary for.
  Exposed as `unity_game_howto` + an intent ("X nasil oynanir / how to play X / X kontrolleri") that uses
  `kontrolleri` as a token-PREFIX and is placed after assess + anatomy, before build -- verified it steals
  none of build / anatomy / assess / showcase / campaign. The player-facing complement to the (technical)
  anatomy. +38 tests. 1694 passed.

- [x] **Speedrun -- the 19th game type, the first that races a DEADLINE TO A DESTINATION (cycle 110).**
  Back to BREADTH. New `deadline` behaviour (AutopilotDeadline): the MIRROR of `timer` -- a countdown that
  SendMessages "PlayerDied" (the LOSE) at zero instead of "Survived" (the WIN). `plan_speedrun_game`: a
  WASD player at the near end races to a `goal` at the far end before the deadline runs out, with N
  `killzone` hazards between that RESPAWN you (a setback that bleeds the clock). The GameManager runs
  deadline + gameover (reaching the goal -> ReachedGoal WIN, which fires first if you make it) + title +
  sound. Distinct from time_survival (outlast a timer to WIN) and collector_race (collect all before the
  clock): you race a deadline to a PLACE, and the hazards are NOT tagged Enemy so the only win is the exit.
  critique stays clean (the goal is the WIN, the deadline the LOSE -- no false flags); the how-to deriver
  now reads `deadline` (win "...before the deadline runs out", a deadline threat, lose "the deadline runs
  out"). Registered behaviour (NEEDS_SCRIPT / aliases that do NOT include "sure"/"zaman" so it can't shadow
  the timer / templates / game-feel category) + blueprint + detect/wants_game intent (distinct terms) +
  _GAME_EXAMPLES (19/19 showcase routing). Live-proved 19/19 self-audit (valid+playable+coherent) +
  deadline fires PlayerDied not Survived (ascii+balanced) + the derived how-to races the clock + intent
  routes without stealing runner/dodge/the clock games. Generate-only; deterministic. +49 tests. 1743 passed.

- [x] **Composer gains a `deadline` element -- the speedrun mechanic, now freeform (cycle 111).**
  `compose_custom_game(deadline=True)` wires the cycle-110 LOSING countdown into a custom game: it implies
  a goal (auto-added -- the WIN) and the GameManager runs `deadline` + `gameover` (PlayerDied at zero =
  the LOSE), so any element mix can become a "race the clock to the exit" game. The NL parser learns it as
  a PHRASE FLAG (`_SPEC_FLAG_PHRASES`): the deadline phrases ("deadline" / "beat the clock" / "sure
  dolmadan" / "sayac dolmadan" ...) are detected + STRIPPED before the single-word flags so an inner timer
  word can't ALSO trip the WINNING timer, plus a mutual-exclusion rule (a named deadline forces timer off)
  -- the two countdown semantics never both light up. Both compose tools + the keyword-less route + the
  composer report (a new phrase-flags section) + `_COMPOSER_COUPLINGS` carry it; `compose_health` grew to
  16 cases, all valid+playable+coherent (studio report "16/16 composer cases"). The cycle-110 how-to
  deriver already reads `deadline`, so a composed deadline game self-documents. Live-proved coherent +
  playable + auto-goal, no timer double-fire, freeform composes while the speedrun preset still builds.
  Generate-only; deterministic. +6 tests. 1749 passed.

- [x] **Composer `player_flash` juice flag -- hit feedback on the player (cycle 112).** The cycle-101
  `hitflash` (until now boss-only) becomes player-facing in the composer. `compose_custom_game(player_flash
  =True)` appends `hitflash` to the player kit, so the player flashes red when it takes damage. The juice
  is real because enemies + turrets damage the player via `SendMessage("TakeDamage")`, which the
  same-object `AutopilotHitFlash` reacts to alongside `AutopilotHealth` -- purely cosmetic + decoupled, so
  validity/playability/coherence are unchanged (a no-op when nothing can hit you). NL parser learns it as
  a flag ("hitflash"/"parlama"/"flash"/...); deliberately NOT a game ELEMENT, so a juice-word-only prompt
  does NOT route to the composer while element + juice composes WITH the flag on. Both compose tools +
  couplings + report carry it; `compose_health` grew to 17 cases, all clean. Low churn (additive). Future:
  extend player hit-flash to the combat PRESETS (arena/horde/boss/time_survival/twin_stick) -- deferred
  this cycle to avoid the multi-blueprint exact-set churn. Generate-only; deterministic. +6 tests. 1755 passed.

- [x] **Player hit-flash in the combat PRESETS (cycle 113).** The cycle-112 deferred item, landed. A
  single coherent rule -- IF THE PLAYER CAN BE HURT, IT FLASHES WHEN HURT -- applied to every preset whose
  player carries `health`: arena, horde, time_survival, hold, boss, twin_stick. Each gives the player
  `hitflash` after `health`, so it flashes red on every enemy/turret hit (they damage it via
  `SendMessage("TakeDamage")`, which `AutopilotHitFlash` reacts to alongside `AutopilotHealth`). Purely
  cosmetic + decoupled: studio_health stays 19/19, object counts + seed-independence untouched;
  unique_scripts unchanged for arena/boss (already ran hitflash on the boss/mini-boss) and +1 for the
  other four. Non-combat / no-player-health types stay untouched (a flash with no damage source is never
  seen). Mechanical churn: 6 player-set assertions updated, no new tests. Generate-only; deterministic.
  +0 tests. 1755 passed.

- [x] **Key-and-door -- the 20th game type, the first with a FETCH-THEN-EXIT gate (cycle 114).** New
  `lockgoal` behaviour (AutopilotLockGoal): a LOCKED exit that counts the remaining "Key_*" by name
  (decoupled, like collectrace) and stays locked until none remain, then -- when the player reaches it --
  SendMessages "ReachedGoal" (the WIN, reusing gameover's hook). `plan_keydoor_game`: a WASD player +
  score grabs N keys (reusing `collectible`, named Key_*) and dodges N `killzone` hazards, then reaches
  the unlocked Door. Distinct from collectathon (collect AT the goal, no gate) and collector_race (a
  clock): the keys UNLOCK a separate exit you must then reach; no hard lose (a hazard respawns you). QA
  surfaces learned lockgoal on the collectrace precedent: INTERACTIVE (playable), counts as a goal/exit
  (has_goal -> no false 'no goal' warning), a WIN trigger in the critique (gameover+lockgoal not flagged),
  'world' category (drift guard), how-to "collect every key to unlock the exit, then reach it." Registered
  behaviour + blueprint + intent (distinct phrases, NOT bare "kapi" = the composer goal flag, no theft) +
  _GAME_EXAMPLES (20/20 routing). Live-proved 20/20 self-audit + lockgoal counts keys/wins on reach + the
  how-to + intent (no theft). Generate-only; deterministic. +47 tests. 1802 passed.

- [x] **Behaviour reference -- the 8th self-awareness surface, BEHAVIOUR granularity (cycle 115).** The
  studio could describe its GAMES (catalog/showcase/anatomy/howto) and COMPOSER ELEMENTS (composer-report)
  but never its building BLOCKS. New `build_behaviour_reference()`: per canonical scripted behaviour,
  grouped by category, the generated MonoBehaviour CLASS (live from _SCRIPT_TEMPLATES), a one-line purpose
  (`_BEHAVIOUR_PURPOSES`, 39 entries), and which game types use it (code-derived). Class + used-by are
  derived (never drift); the purpose key set is drift-guarded against the category list (no block silently
  omitted). Chosen over a difficulty/balance heuristic, which would invite debatable rankings against the
  project's honesty bar. Exposed as `unity_behaviour_reference` + an intent ("davranis sozlugu / hangi
  davranislar / behaviour reference / list behaviours"), verified it steals neither the game catalog nor
  the composer report nor a build. Live-proved 39/39 documented + derived columns + intent (no theft).
  Generate-only; deterministic. +13 tests. 1815 passed.

> Check items off in this file as they land. Add new items as discovered.
