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

    # 2) player: cube, tagged Player, with the WASD controller behaviour
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

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
        "summary": f"Collect-a-thon: ground + WASD player + {n} collectibles + goal ({len(steps)} steps).",
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
