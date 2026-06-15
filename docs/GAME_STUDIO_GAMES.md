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

Turkish/English aliases are accepted (fizik, ağır, oyuncu, toplanabilir, hedef, ölüm/lava,
dalga, devriye, takip, zıpla, …). **Every behaviour listed here is templated** — each generates
a compilable MonoBehaviour (`generate_behaviour_script` returns its source); none are stubs.

## 3. "Build me a game" — intent routing

`plan_unity_fast_action` (and the Unity fast-path) route these to a `unity_build_simple_game`
plan automatically:

- tr: "oyun kur", "oyun yap", "toplama oyunu", "dodge/kaçma oyunu", "sağ kalma / hayatta kalma oyunu", "platform / zıplama oyunu", "kovalamaca / takip oyunu", "oyun iskeleti"
- en: "build me a game", "make a collectathon/dodge/survival/platformer/chase game"

A number in the prompt sets the count ("toplama oyunu yap 8 toplanabilir" → 8).

**Assess (don't build):** "oyunu değerlendir", "dodge oyununu analiz et", "oynanabilir mi",
"assess the game", "is the game playable" route to `unity_assess_game` instead — a read-only
readiness report (counts + playable verdict + warnings, no scene changes, no bridge). The assess
intent is checked *before* the build intent, so a prompt with both a game type and an assess verb
("dodge oyununu değerlendir") is analysed, not rebuilt. Scene-level "analiz"/"qa"/"performans"
(no game context) still route to the visual-QA / profiling tools.

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

## 6. Living scenes (decorative, not a game)

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
