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
| `collectathon` | Ground + WASD player + N collectibles (pickups) + a goal zone | "bana bir toplama oyunu kur" / "build me a collectathon game" |
| `dodge` | Ground + WASD player + N **moving** hazards (mover+killzone) + goal | "dodge oyunu yap" / "make a dodge game" |
| `survival` | Ground + WASD player + N elevated hazard **spawners** (raining cubes) | "sağ kalma oyunu kur" / "build me a survival game" |
| `platformer` | Ground + WASD+**jump** player + N solid platforms climbing like a staircase + a goal on top | "platform oyunu yap" / "build me a platformer" |

`collectible_count` is the count of the main repeated element (collectibles / hazards /
spawners / platforms). The blueprint registry is `core/game_blueprint.BLUEPRINTS`;
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
| `collectible` | AutopilotCollectible | OnTriggerEnter(Player) → Destroy (pickup) |
| `goal` | AutopilotGoalZone | OnTriggerEnter(Player) → win flag |
| `killzone` | AutopilotKillZone | OnTriggerEnter(Player) → respawn |
| `spawner` | AutopilotSpawner | InvokeRepeating spawns physics cubes (waves) |

Turkish/English aliases are accepted (fizik, ağır, oyuncu, toplanabilir, hedef, ölüm/lava,
dalga, …). **Declared but not yet templated** (they report `needs_script` with no source
yet): `bob`, `bounce`, `chase`, `follow`, `orbit`, `patrol`, `wander` — good next additions.

## 3. "Build me a game" — intent routing

`plan_unity_fast_action` (and the Unity fast-path) route these to a `unity_build_simple_game`
plan automatically:

- tr: "oyun kur", "oyun yap", "toplama oyunu", "dodge/kaçma oyunu", "sağ kalma / hayatta kalma oyunu", "platform / zıplama oyunu", "oyun iskeleti"
- en: "build me a game", "make a collectathon/dodge/survival/platformer game"

A number in the prompt sets the count ("toplama oyunu yap 8 toplanabilir" → 8).

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

> See `GAME_STUDIO_TOOLS.md` for the full tool catalog and `GAME_STUDIO_PROGRESS.md` for the
> per-cycle history of how this was built.
