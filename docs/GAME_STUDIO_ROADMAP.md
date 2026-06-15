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

> Check items off in this file as they land. Add new items as discovered.
