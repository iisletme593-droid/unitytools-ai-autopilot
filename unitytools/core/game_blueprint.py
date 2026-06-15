"""Game blueprints — compose the gameplay building blocks into a playable game.

The peak of the "scene decorator -> game maker" arc: instead of one object at a
time, plan a whole minimal game. plan_collectathon_game emits an ordered list of
steps that reuse the existing tools (primitives, placement, tag) and scripted
behaviours (player controller, collectible, goal). Pure + deterministic; the
unity_build_simple_game tool turns it into actions (opt-in, since script behaviours
trigger Unity recompiles).

A step is either:
  * {"tool": "<unity_tool>", "kwargs": {...}}        — a direct tool call
  * {"script_behaviour": {"object": str, "behaviour": str}}  — attach a MonoBehaviour
"""
from __future__ import annotations

from typing import Any


def plan_collectathon_game(collectible_count: int = 5, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a minimal collect-a-thon: ground, a controllable player, N pickups, a goal.

    Returns {ok, game, summary, collectible_count, steps}. Deterministic — no I/O.
    """
    n = max(1, min(int(collectible_count), 50))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player: cube, tagged Player, with the WASD controller behaviour and the
    #    score HUD (collectibles message the player to add points, so the counter
    #    lives on the player — one persistent object, no stray HUD GameObject).
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})

    # 3) collectibles: N spheres in a ring, each a pickup trigger
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Sphere",
            "count": n,
            "pattern": "circle",
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Collectible",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Collectible_{i}", "behaviour": "collectible"}})

    # 4) goal zone
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "collectathon",
        "summary": f"Collect-a-thon: ground + WASD player + score HUD + {n} collectibles + goal ({len(steps)} steps).",
        "collectible_count": n,
        "steps": steps,
    }


def plan_dodge_game(obstacle_count: int = 6, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a dodge game: ground, a controllable player, N MOVING hazards, a goal.

    Each hazard composes two behaviours (mover + killzone) so it slides around and
    respawns the player on contact — a different game from the same building blocks.
    Same return schema as plan_collectathon_game.
    """
    n = max(1, min(int(obstacle_count), 50))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "scatter",
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Obstacle",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Obstacle_{i}", "behaviour": "mover"}})
        steps.append({"script_behaviour": {"object": f"Obstacle_{i}", "behaviour": "killzone"}})

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "dodge",
        "summary": f"Dodge: ground + WASD player + {n} moving hazards + goal ({len(steps)} steps).",
        "obstacle_count": n,
        "steps": steps,
    }


def plan_survival_game(spawner_count: int = 3, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a survival game: ground, a controllable player, M elevated spawners that
    rain physics-cube hazards in waves. Survive the onslaught. Same return schema.
    """
    n = max(1, min(int(spawner_count), 20))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(4.0, size / float(n)),
            "origin_y": 6.0,           # elevated so spawned cubes fall onto the arena
            "name_prefix": "Spawner",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Spawner_{i}", "behaviour": "spawner"}})

    return {
        "ok": True,
        "game": "survival",
        "summary": f"Survival: ground + WASD player + {n} hazard spawners ({len(steps)} steps).",
        "spawner_count": n,
        "steps": steps,
    }


def plan_platformer_game(platform_count: int = 5, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a platformer: ground, a WASD+jump player, N solid platforms climbing
    like a staircase, and a goal at the top you reach by jumping up them.

    The player already has a Space-to-jump controller; the platforms are plain
    cubes (which carry a BoxCollider) made explicitly solid with the
    ``static_obstacle`` physics behaviour, so they are jump-on-able and need no
    recompile. Each platform sits a step higher (and further) than the last.
    Same return schema as the other plan_*_game blueprints.
    """
    n = max(1, min(int(platform_count), 30))
    size = max(6.0, float(arena_size))
    step_y = 1.5   # how much higher each platform sits
    step_z = 3.0   # how much further out each platform sits (staircase depth)
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player at the foot of the staircase: WASD + Space jump
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    # 3) platforms: cubes climbing up-and-away, each a solid (static_obstacle) ledge
    top_y = 0.0
    top_z = 0.0
    for i in range(n):
        py = 1.0 + i * step_y
        pz = (i + 1) * step_z
        top_y, top_z = py, pz
        steps.append({
            "tool": "unity_create_primitive",
            "kwargs": {"type": "Cube", "name": f"Platform_{i}", "position_y": py, "position_z": pz},
        })
        steps.append({
            "tool": "unity_add_gameplay_behaviour",
            "kwargs": {"object_name": f"Platform_{i}", "behaviour": "static_obstacle"},
        })

    # 4) goal sitting on top of the last (highest) platform
    steps.append({
        "tool": "unity_create_primitive",
        "kwargs": {"type": "Cube", "name": "Goal", "position_y": top_y + 1.0, "position_z": top_z},
    })
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "platformer",
        "summary": f"Platformer: ground + WASD+jump player + {n} climbing platforms + goal on top ({len(steps)} steps).",
        "platform_count": n,
        "steps": steps,
    }


def plan_chase_game(enemy_count: int = 4, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a chase game: ground, a WASD+jump player with a score HUD, N enemies
    that CHASE the player (follow + killzone — touch you and you respawn), and a
    ring of collectibles to grab while you run. Showcases the new `follow`
    behaviour combined with `killzone` (the same compose-two-behaviours trick the
    dodge game uses for moving hazards). Same return schema as the others.
    """
    n = max(1, min(int(enemy_count), 30))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player: tagged, controllable, carrying the score HUD
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})

    # 3) enemies: a ring of cubes that chase the player and respawn it on contact
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(3.0, size / float(n)),
            "name_prefix": "Enemy",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "follow"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "killzone"}})

    # 4) collectibles: a tighter ring to grab while escaping (+1 each to the HUD)
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Sphere",
            "count": n,
            "pattern": "circle",
            "spacing": max(2.0, size / (2.0 * float(n))),
            "name_prefix": "Collectible",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Collectible_{i}", "behaviour": "collectible"}})

    # 5) goal zone
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "chase",
        "summary": f"Chase: ground + WASD player + score HUD + {n} chasing enemies + {n} collectibles + goal ({len(steps)} steps).",
        "enemy_count": n,
        "steps": steps,
    }


# Decorative (non-gameplay) scripted behaviours that give a scene "juice".
DECOR_BEHAVIOURS = ["bob", "orbit", "rotate", "wander"]


def plan_ambient_decor(
    count: int = 8,
    arena_size: float = 16.0,
    primitive: str = "Sphere",
    pattern: str = "circle",
    behaviours: list[str] | None = None,
) -> dict[str, Any]:
    """Plan a "living scene": place N props and give each a decorative scripted
    behaviour (bob/orbit/rotate/wander, cycled) so the scene breathes. This is
    juice, not a game — there is no player or goal. Same step schema as the game
    blueprints (tool + script_behaviour). Pure + deterministic.

    Unknown/aliased behaviour names are normalized and validated against the
    template registry; anything without a template is dropped (falls back to the
    default decor set if nothing valid remains) so the plan never references a
    phantom behaviour.
    """
    from .gameplay import generate_behaviour_script, normalize_behaviour

    n = max(1, min(int(count), 200))
    size = max(4.0, float(arena_size))
    requested = behaviours if behaviours else DECOR_BEHAVIOURS
    beh = [normalize_behaviour(b) for b in requested]
    beh = [b for b in beh if generate_behaviour_script(b).get("ok")] or list(DECOR_BEHAVIOURS)

    steps: list[dict[str, Any]] = []
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": primitive,
            "count": n,
            "pattern": pattern,
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Decor",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Decor_{i}", "behaviour": beh[i % len(beh)]}})

    return {
        "ok": True,
        "decor": "ambient",
        "summary": f"Living scene: {n} {primitive}(s) with cycled {'/'.join(beh)} ({len(steps)} steps).",
        "count": n,
        "behaviours": beh,
        "steps": steps,
    }


def group_execution_plan(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Split a blueprint's steps for efficient execution.

    Returns {geometry, script_behaviours, attachments}. ``script_behaviours`` is
    the DISTINCT behaviour list (so each MonoBehaviour is imported once → a single
    recompile, instead of one per object); ``attachments`` is every (object,
    behaviour) to add as a component after compilation. Geometry runs first so the
    target objects exist before attaching.
    """
    geometry: list[dict[str, Any]] = []
    attachments: list[dict[str, str]] = []
    script_behaviours: list[str] = []
    for step in steps:
        if "tool" in step:
            geometry.append(step)
        elif "script_behaviour" in step:
            sb = step["script_behaviour"]
            attachments.append({"object": sb["object"], "behaviour": sb["behaviour"]})
            if sb["behaviour"] not in script_behaviours:
                script_behaviours.append(sb["behaviour"])
    return {"geometry": geometry, "script_behaviours": script_behaviours, "attachments": attachments}


# Registry of game blueprints (game_type -> planner). Each planner takes the count
# of its main repeated element and returns {ok, game, summary, steps, ...}.
BLUEPRINTS = {
    "collectathon": plan_collectathon_game,
    "dodge": plan_dodge_game,
    "survival": plan_survival_game,
    "platformer": plan_platformer_game,
    "chase": plan_chase_game,
}


def list_blueprints() -> list[str]:
    return sorted(BLUEPRINTS)


def _apply_seed(plan: dict[str, Any], game_type: str, count: int, seed: object) -> dict[str, Any]:
    """Deterministically vary a plan from a seed, without editing any blueprint.

    Records the seed on the plan and gives each placement step a reproducible
    ``jitter`` (same seed -> same jitter). Pure: a None seed is a no-op, so the
    plan is identical to the un-seeded one. Layout (counts, behaviours) is
    unchanged — only the scatter is perturbed, so seeded games stay playable.
    """
    if seed is None:
        return plan
    from .procedural import seeded_rng

    rng = seeded_rng(f"{game_type}:{count}:{seed}")
    for step in plan.get("steps", []):
        if step.get("tool") == "unity_place_primitives":
            step["kwargs"]["jitter"] = round(rng.uniform(0.5, 2.0), 3)
    plan["seed"] = seed
    plan["summary"] = f"{plan.get('summary', '').rstrip('.')} [seed {seed}]."
    return plan


def plan_game(game_type: str = "collectathon", count: int = 5, seed: object = None) -> dict[str, Any]:
    """Dispatch to a blueprint planner by game_type (unknown -> collectathon).

    An optional ``seed`` makes the result reproducibly varied: the same seed
    always yields the same plan; ``seed=None`` (default) is the plain blueprint.
    """
    gt = (game_type or "collectathon").strip().lower()
    planner = BLUEPRINTS.get(gt, plan_collectathon_game)
    return _apply_seed(planner(count), gt, count, seed)


def _difficulty_labels(n: int) -> list[str]:
    """Human difficulty tags for n variations, easy -> hard."""
    presets = {1: ["standard"], 2: ["easy", "hard"], 3: ["easy", "medium", "hard"],
               4: ["easy", "medium", "hard", "extreme"]}
    return presets.get(n, [f"level-{i + 1}" for i in range(n)])


def plan_game_variations(
    game_type: str = "collectathon",
    counts: list[int] | None = None,
    arena_size: float = 20.0,
) -> dict[str, Any]:
    """Generate several variations of ONE game type at different difficulties.

    For each count (sorted ascending so easy->hard is monotonic) it builds the
    plan and attaches a readiness summary from game_qa. Pure + deterministic; no
    bridge, no scene changes. Returns {ok, game_type, count, variations:[{label,
    params, summary, object_count, unique_scripts, playable, warnings}]}.
    """
    from .game_qa import assess_game_readiness  # lazy: game_qa imports this module

    gt = (game_type or "collectathon").strip().lower()
    if gt not in BLUEPRINTS:
        gt = "collectathon"
    planner = BLUEPRINTS[gt]

    raw = counts if counts else [3, 5, 8]
    clean = sorted({max(1, int(c)) for c in raw})         # dedupe + clamp + ascending
    labels = _difficulty_labels(len(clean))

    variations: list[dict[str, Any]] = []
    for label, c in zip(labels, clean):
        plan = planner(c, arena_size)
        report = assess_game_readiness(plan)
        variations.append({
            "label": label,
            "params": {"count": c, "arena_size": float(arena_size)},
            "summary": plan.get("summary", ""),
            "object_count": report["object_count"],
            "unique_scripts": report["unique_scripts"],
            "playable": report["playable"],
            "warnings": report["warnings"],
        })

    return {"ok": True, "game_type": gt, "count": len(variations), "variations": variations}
