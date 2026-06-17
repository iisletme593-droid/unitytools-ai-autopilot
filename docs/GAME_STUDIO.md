# 🎮 Autonomous Game Studio

A self-operating game studio built on the UnityTools autopilot: describe a game in plain
language (Turkish or English) and it plans — and on request builds — a playable Unity scene.
This page is the one-screen tour; every section links to the deep doc.

> Built incrementally on branch `autonomous/game-studio`, one verified change per cycle, with
> `pytest` gating every step. See [GAME_STUDIO_PROGRESS.md](GAME_STUDIO_PROGRESS.md) for the log.

## What it makes

Nineteen playable game types (plus a freeform **custom composer** — describe an element mix and it
assembles a custom game from the same blocks), each composed from the same gameplay building blocks:

| game_type | One-liner |
|-----------|-----------|
| `collectathon` | WASD player + score HUD, grab all the collectibles, reach the goal |
| `dodge` | Survive moving hazards (mover + killzone) and reach the goal |
| `survival` | Brave elevated spawners raining physics-cube chaos + deadly floor patches and reach the exit to win |
| `platformer` | Jump up a staircase of solid platforms to a goal on top, timing your jumps past patrolling hazards on every other ledge (touch one and you respawn) |
| `chase` | Outrun enemies that hunt the player while you grab collectibles |
| `maze` | Escape a deterministic, always-solvable procedural labyrinth (seeded), now with deadly traps in the dead-ends (a wrong turn respawns you — but the solution path is always trap-free) |
| `arena` | A blocky brawler: an armed player (health + attack) vs N enemies that chase and attack back, plus a single high-HP **mini-boss** climax (its own HP bar) |
| `horde` | A survival-brawler: a fully-armed player vs escalating waves of enemies from a central spawner |
| `runner` | An endless runner: an auto-running player dodging a weaving lane of obstacles, distance is the score |
| `tower_defense` | Ranged towers + a mobile hero defend a base from waves of enemies that march to it; lose if the base falls |
| `time_survival` | Outlast the clock: an armed player fights N enemies and wins by surviving the countdown (or clearing them), loses on death |
| `stealth` | Slip past N patrolling guards (line-of-sight) and reach the exit unseen to win; get spotted to lose. The first type won by avoiding combat |
| `puzzle` | A sokoban: push N crates onto N targets; solve them all to win. A push mechanic, no combat or timer |
| `hold` | King of the hill: hold a central zone (no attack) while N enemies try to push you out; fill the meter to win, die to lose |
| `escort` | An escort/VIP mission: a moving NPC (tagged Player) walks itself to the goal while enemies march at it; you play a separate Hero bodyguard who clears them. Deliver the VIP to win, lose if it falls. The first type won by protecting something that isn't you |
| `boss` | A boss fight: an armed player (melee + ranged) duels one (or more) high-HP boss with an on-screen HP bar; whittle it down to win, die to lose. The first sustained single-target fight |
| `collector_race` | A collector race: grab all N collectibles before a countdown runs out (collect them all to win, run out of time to lose). The first type where the clock is your enemy |
| `twin_stick` | A twin-stick shooter: a ranged-only kiter (auto-aim gun, no melee) backs away from a ring of chasing enemies and guns them down; clear them to win, get cornered to lose. The first ranged-primary type |
| `speedrun` | A race to the exit: cross from the start to the goal before a **losing countdown** (the new `deadline`) runs out, dodging deadly hazards that respawn you and bleed the clock. The first type that races a deadline to a destination |

Plus **living scenes** — decorative `bob`/`orbit`/`rotate`/`wander` motion as scene juice (not a game).

## How to drive it (natural language)

The deterministic fast-path (`plan_unity_fast_action`) routes plain commands to tools — no LLM guess:

| You say… | It runs |
|----------|---------|
| "bana bir dodge oyunu kur", "build me a chase game" | `unity_build_simple_game` |
| "zor dodge oyunu yap" (kolay/orta/zor → 3/5/8) | `unity_build_simple_game` (sized) |
| "oyunu değerlendir", "is the game playable" | `unity_assess_game` |
| "dodge varyasyonları göster", "easy/medium/hard" | `unity_game_variations` |
| "arena kampanyası", "3 seviyeli dodge", "horde campaign" | `unity_plan_campaign` |
| "hangi oyunlar yapabilirsin", "what games" | `unity_game_catalog` |
| "örnek oyunlar göster", "show me examples", "game examples" | `unity_game_showcase` |
| "arena oyununun yapısı", "X oyunu anatomisi", "breakdown of the X game" | `unity_game_anatomy` |
| "arena oyunu nasıl oynanır", "how to play the X game", "X kontrolleri" | `unity_game_howto` |
| "özel oyun: 5 düşman 3 toplanabilir bir sayaç", "custom game" | `unity_compose_game` |
| "studio raporu", "yeteneklerin", "capabilities", "what can you do" | `unity_studio_report` |
| "studio sağlığı", "sağlık denetimi", "studio health", "her şey yolunda mı" | `unity_studio_health` |
| "composer raporu", "ne tarif edebilirim", "what can i compose", "hangi öğeler" | `unity_composer_report` |
| "sahneyi canlandır", "animate the scene" | `unity_animate_group` |
| "dodge oyununu boss olarak kaydet", "save as X" | `unity_save_game` |
| "boss oyununu yükle", "load X" / "kayıtlı oyunlar" | `unity_load_game` / `unity_list_saved_games` |

An explicit number always wins ("dodge oyunu yap 8" → 8). The local LLM master planner is also given a
code-derived capability summary so it knows these games exist.

## Persistence (save / load / import)

Games are no longer ephemeral. A game's plan can be saved to disk as versioned JSON and loaded back
exactly — so you can build a library, share games, or replay them.

- **Save:** "… olarak kaydet" / "save as X" → `unity_save_game` writes `<name>.json` under the games
  directory (`UNITYTOOLS_GAMES_DIR`, else `.unitytools/games`).
- **Load / list:** "oyunu yükle X" → `unity_load_game` (returns the plan only), "kayıtlı oyunlar" →
  `unity_list_saved_games`.
- **Import / build:** `unity_import_game(json)` parses + **validates** external JSON;
  `unity_build_loaded_game(name)` loads, re-validates, and (with `execute=True`) builds it.

**Safety:** save names are sanitized to a slug **and** re-checked with `safe_contained_path`, so no
name can escape the games root (two-layer path-traversal defense). External JSON is treated as
untrusted: `validate_plan` rejects any step that isn't a whitelisted tool call or a real templated
behaviour. Saving never changes the scene; loading returns a plan; building is `execute=False` by
default.

## How it works (architecture)

```
natural language ─▶ plan_unity_fast_action ─▶ blueprint (plan_*_game)
                                                  │  steps: {tool, kwargs} | {script_behaviour}
                                                  ▼
                              group_execution_plan  (dedupe scripts → ONE recompile)
                                                  ▼
                     execute=False: just the plan   │   execute=True: build geometry,
                     (safe, no scene change)         │   import each unique script once,
                                                     ▼   wait for compile, attach components
                                              live Unity scene
```

- **Blueprints** (`core/game_blueprint.py`) compose primitives + behaviours into a game.
- **Behaviours** (`core/gameplay.py`): physics (collider/rigidbody, applied instantly) and scripted
  (generated MonoBehaviour source — player, collectible, goal, killzone, spawner, score, follow,
  patrol, bob, …). Every declared behaviour has a real, compilable template (no stubs).
- **QA** (`core/game_qa.py`): `assess_game_readiness` / `summarize_catalog` analyse a plan (counts,
  playable verdict, warnings) with no bridge, so the studio can sanity-check itself before building.

## Safety

- `execute=False` is the **default** everywhere: you get the step plan, the scene is untouched.
- `execute=True` imports scripts, which **reloads the Unity domain (a recompile)** and briefly drops
  the bridge — run it with the editor in focus. Unique scripts are imported once to collapse N
  recompiles into one.
- All planning, QA, variations and catalog tools are **pure** (no bridge, no scene changes).

## Where to read more

- [GAME_STUDIO_GAMES.md](GAME_STUDIO_GAMES.md) — games, behaviour catalog, intent phrases, variations, catalog
- [GAME_STUDIO_TOOLS.md](GAME_STUDIO_TOOLS.md) — the full `unity_*` tool catalog
- [GAME_STUDIO_ARCHITECTURE.md](GAME_STUDIO_ARCHITECTURE.md) — the orchestrator / dual-agent design
- [GAME_STUDIO_ROADMAP.md](GAME_STUDIO_ROADMAP.md) — backlog · [GAME_STUDIO_PROGRESS.md](GAME_STUDIO_PROGRESS.md) — per-cycle log
