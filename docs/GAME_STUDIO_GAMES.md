# Game Studio — Games & Gameplay Catalog

What the autopilot can author beyond decorating scenes: **gameplay**. This page is the
reference for the game blueprints, the behaviour catalog, and how to drive them.
Everything here is verified against the code by `tests/test_games_doc.py` (no phantom
names).

## 1. Game types (blueprints)

`unity_build_simple_game(game_type=…, collectible_count=N, execute=False)` plans (and
optionally builds) a complete playable game by composing the building blocks below.

| game_type | What it is | Example command (tr / en) |
|-----------|-----------|----------------------------|
| `collectathon` | Ground + WASD player + an on-screen **score HUD** + N collectibles (each +1) + a goal zone | "bana bir toplama oyunu kur" / "build me a collectathon game" |
| `dodge` | Ground + WASD player + N **moving** hazards (mover+killzone) + goal | "dodge oyunu yap" / "make a dodge game" |
| `survival` | Ground + WASD player + N elevated hazard **spawners** (raining cubes) | "sağ kalma oyunu kur" / "build me a survival game" |
| `platformer` | Ground + WASD+**jump** player + N solid platforms climbing like a staircase + a goal on top | "platform oyunu yap" / "build me a platformer" |
| `chase` | Ground + player + score HUD + N enemies that **chase** you (follow + killzone) + N collectibles to grab while escaping + goal | "kovalamaca oyunu kur" / "build me a chase game" |
| `maze` | A deterministic, always-solvable procedural **labyrinth** (seeded): solid walls + player at the entrance + goal at the exit. `collectible_count` is the maze size (3–8) | "labirent oyunu kur" / "build me a maze game" |

`collectible_count` is the count of the main repeated element (collectibles / hazards /
spawners / platforms / enemies). The blueprint registry is `core/game_blueprint.BLUEPRINTS`;
`list_blueprints()` lists them and `plan_game(game_type, count)` dispatches.

## 2. Gameplay behaviour catalog

Give one object a behaviour with `unity_add_gameplay_behaviour(object, behaviour)`
(physics, composed from existing tools) or `unity_add_script_behaviour` /
`unity_apply_script_behaviour` (scripted, generates a MonoBehaviour).

### Physics (no script — composes Rigidbody/collider, applies instantly)
| behaviour | Effect |
|-----------|--------|
| `physics` / `falling` | Gravity-driven rigid body + collider |
| `heavy` | Physics with high mass |
| `floaty` | Physics with high drag |
| `kinematic` | Kinematic body (script-moved platform) |
| `static_obstacle` | Collider only — a solid, non-moving obstacle |

### Scripted (generates a MonoBehaviour — needs a Unity recompile to attach)
| behaviour | Class | Effect |
|-----------|-------|--------|
| `rotate` / `spin` / `spinner` | AutopilotRotator | Spins every frame |
| `move` / `mover` | AutopilotMover | Translates every frame |
| `player` / `controller` | AutopilotPlayerController | WASD movement + Space jump |
| `collectible` | AutopilotCollectible | OnTriggerEnter(Player) → +1 score (SendMessage) then Destroy (pickup) |
| `goal` | AutopilotGoalZone | OnTriggerEnter(Player) → win flag |
| `killzone` | AutopilotKillZone | OnTriggerEnter(Player) → respawn |
| `spawner` | AutopilotSpawner | InvokeRepeating spawns physics cubes (waves) |
| `score` / `skor` / `puan` / `hud` | AutopilotScore | Global counter + top-left OnGUI HUD; `Add(n)` static or `SendMessage("AddScore", n)` |
| `bob` | AutopilotBob | Bobs up/down on a sine wave around its start position |
| `bounce` / `zıpla` | AutopilotBounce | Bounces off its rest height (abs-sine, never dips below) |
| `patrol` / `devriye` | AutopilotPatrol | Patrols back and forth between two points (PingPong) |
| `follow` / `chase` / `takip` | AutopilotFollower | Chases the Player (tag) with MoveTowards; no-op if absent |
| `orbit` | AutopilotOrbit | Orbits its start point on an axis (RotateAround) |
| `wander` | AutopilotWander | Drifts to random points near home, re-targeting on a timer |
| `health` / `can` / `sağlık` / `hp` | AutopilotHealth | Hit points + `TakeDamage(n)`/`Heal(n)`; death → respawn (or destroy); top-right HP HUD |
| `attack` / `saldırı` / `vur` / `hit` | AutopilotAttack | Damages a tagged target in `range` every `cooldown` via `SendMessage("TakeDamage")` — pairs with `health`, no hard reference |

The last two are the start of the **action-RPG combat** building blocks (P11): `attack` deals damage
that `health` receives, fully decoupled. Turkish/English aliases are accepted (fizik, ağır, oyuncu,
toplanabilir, hedef, ölüm/lava, dalga, devriye, takip, zıpla, can, saldırı, …). **Every behaviour
listed here is templated** — each generates a compilable MonoBehaviour (`generate_behaviour_script`
returns its source); none are stubs.

## 3. "Build me a game" — intent routing

`plan_unity_fast_action` (and the Unity fast-path) route these to a `unity_build_simple_game`
plan automatically:

- tr: "oyun kur", "oyun yap", "toplama oyunu", "dodge/kaçma oyunu", "sağ kalma / hayatta kalma oyunu", "platform / zıplama oyunu", "kovalamaca / takip oyunu", "labirent oyunu", "oyun iskeleti"
- en: "build me a game", "make a collectathon/dodge/survival/platformer/chase/maze game"

A number in the prompt sets the count ("toplama oyunu yap 8 toplanabilir" → 8).

**Seed (reproducible variety):** add "tohum 42" / "seed 42" / "seed:abc" (or "42 tohumuyla") to a
build to make the layout reproducible — the same seed always builds the same game, a different seed a
different (but deterministic) one. The seed is recognised separately from the count, so "zor dodge
oyunu kur tohum 7" is difficulty-hard (8) with seed 7. The seed is recorded in the plan and survives
save/load and export, so seeded games are shareable.

**Assess (don't build):** "oyunu değerlendir", "dodge oyununu analiz et", "oynanabilir mi",
"assess the game", "is the game playable" route to `unity_assess_game` instead — a read-only
readiness report (counts + playable verdict + warnings, no scene changes, no bridge). The assess
intent is checked *before* the build intent, so a prompt with both a game type and an assess verb
("dodge oyununu değerlendir") is analysed, not rebuilt. Scene-level "analiz"/"qa"/"performans"
(no game context) still route to the visual-QA / profiling tools.

**Save / load / list (P8 persistence):**
- "oyunu kaydet", "dodge oyununu **boss olarak** kaydet", "save the game **as** level1",
  `kaydet "my level"` → `unity_save_game` (writes a JSON file under the games directory; the name is
  taken from quotes / "as X" / "X olarak", else the game type, and is sanitized + traversal-guarded).
- "oyunu yükle boss", "boss oyununu yükle", "load game level1" → `unity_load_game` (returns the saved
  **plan only** — it does not build it).
- "kayıtlı oyunlar", "saved games", "diskteki oyunlar" → `unity_list_saved_games`.

These use distinctive verbs (kaydet/yükle/kayıtlı/save/load) and are checked before build, so
"dodge oyununu kaydet" saves rather than rebuilds; "kayıtlı oyunlar" (disk) stays distinct from
"hangi oyunlar" (catalog). Scene-level "save"/"geri yükle" without a game context are not touched.

## 4. execute=False vs execute=True (recompile note)

- `execute=False` (default): returns the **step plan** only. No scene changes — safe to call
  anytime, including unattended.
- `execute=True`: builds the geometry and imports the behaviour scripts. **Importing a script
  reloads the Unity domain (a recompile)**, which briefly drops the bridge — run it with the
  editor in focus. The execute path imports each *unique* behaviour script once
  (`group_execution_plan`) to collapse N recompiles into one.

## 5. Adding a new blueprint

1. Write `plan_<name>_game(count, ...)` in `core/game_blueprint.py` returning
   `{ok, game, summary, steps}` (steps are `{tool, kwargs}` or `{script_behaviour:{object, behaviour}}`).
2. Register it: `BLUEPRINTS["<name>"] = plan_<name>_game`.
3. Add an intent trigger to `plan_unity_fast_action`'s build-game block.
4. Add a row to the table in §1 and a test.

## 6. Difficulty variations

`unity_game_variations(game_type, counts="3,5,8")` builds the **same** game at several counts and
attaches a readiness summary to each — easy/medium/hard difficulty options the studio can offer
before committing to a build. Pure analysis (no scene changes, no bridge); the pure planner is
`core/game_blueprint.plan_game_variations`. Counts are deduped, clamped (≥1) and sorted ascending
so difficulty rises monotonically (more enemies/collectibles → more objects). Each entry reports
`{label, params, summary, object_count, unique_scripts, playable, warnings}`.

**Intent routing:**
- A **difficulty word** in a build prompt sets the count: kolay/easy → 3, orta/normal/medium → 5,
  zor/hard → 8. An explicit number always wins ("zor dodge oyunu yap 4" → 4). ("çok" is not a
  difficulty trigger — it's a quantity word; "çok zor" still matches "zor".)
- **"varyasyon" / "seçenekler" / "farklı zorluklar" / "variations"** (with a game type) route to
  `unity_game_variations` instead of building — checked before the build intent, so "dodge
  varyasyonları göster" lists the options rather than building one dodge.

## 7. Game catalog (what can I make?)

`unity_game_catalog()` returns a one-glance report of the whole catalog: every game type's summary,
object/script counts, player/goal/score flags, playable verdict, and warnings, plus the full set of
behaviours used across all games and whether they are `all_playable`. Pure (no scene changes, no
bridge); the pure function is `core/game_qa.summarize_catalog`. Routed by intent — "oyun katalogu",
"hangi oyunlar yapabilirsin", "neler yapabilirsin", "what games can you make", "list games" — while
bare "katalog" still means the *scene* catalog (`unity_get_scene_catalog`).

## 8. Living scenes (decorative, not a game)

Not every scene is a game. `unity_animate_group` brings a scene to life: it places N props
and gives each a **decorative** scripted behaviour (`bob` / `orbit` / `rotate` / `wander`,
cycled) so the scene breathes — pure juice, no player or goal. The pure planner is
`core/game_blueprint.plan_ambient_decor` (default decor set `DECOR_BEHAVIOURS`); the tool wraps
it with the same `execute=False` (default, plan only) / `execute=True` (build + one recompile)
contract as the games.

| Tool | What it does | Example command |
|------|--------------|-----------------|
| `unity_animate_group` | Place N props + cycle decorative behaviours over them (living scene) | "sahneyi canlandır" / "animate the scene" / "yaşayan sahne kur" |

`behaviours` is an optional comma-separated subset (e.g. `"bob,rotate"`); unknown names are
normalized and dropped so the plan never references a behaviour without a template.

> See `GAME_STUDIO_TOOLS.md` for the full tool catalog and `GAME_STUDIO_PROGRESS.md` for the
> per-cycle history of how this was built.
