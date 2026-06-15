# 🎮 Autonomous Game Studio

A self-operating game studio built on the UnityTools autopilot: describe a game in plain
language (Turkish or English) and it plans — and on request builds — a playable Unity scene.
This page is the one-screen tour; every section links to the deep doc.

> Built incrementally on branch `autonomous/game-studio`, one verified change per cycle, with
> `pytest` gating every step. See [GAME_STUDIO_PROGRESS.md](GAME_STUDIO_PROGRESS.md) for the log.

## What it makes

Five playable game types, each composed from the same gameplay building blocks:

| game_type | One-liner |
|-----------|-----------|
| `collectathon` | WASD player + score HUD, grab all the collectibles, reach the goal |
| `dodge` | Survive moving hazards (mover + killzone) and reach the goal |
| `survival` | Endure elevated spawners raining physics-cube hazards |
| `platformer` | Jump up a staircase of solid platforms to a goal on top |
| `chase` | Outrun enemies that hunt the player while you grab collectibles |

Plus **living scenes** — decorative `bob`/`orbit`/`rotate`/`wander` motion as scene juice (not a game).

## How to drive it (natural language)

The deterministic fast-path (`plan_unity_fast_action`) routes plain commands to tools — no LLM guess:

| You say… | It runs |
|----------|---------|
| "bana bir dodge oyunu kur", "build me a chase game" | `unity_build_simple_game` |
| "zor dodge oyunu yap" (kolay/orta/zor → 3/5/8) | `unity_build_simple_game` (sized) |
| "oyunu değerlendir", "is the game playable" | `unity_assess_game` |
| "dodge varyasyonları göster", "easy/medium/hard" | `unity_game_variations` |
| "hangi oyunlar yapabilirsin", "what games" | `unity_game_catalog` |
| "sahneyi canlandır", "animate the scene" | `unity_animate_group` |

An explicit number always wins ("dodge oyunu yap 8" → 8). The local LLM master planner is also given a
code-derived capability summary so it knows these games exist.

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
