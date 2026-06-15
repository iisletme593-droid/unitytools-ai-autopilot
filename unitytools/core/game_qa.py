"""Game QA — pure, bridge-free analysis of a blueprint plan.

Given a plan dict from `plan_game`/`plan_*_game`/`plan_ambient_decor` (its `steps`
list), count what the game is made of and judge whether it is actually playable.
No Unity, no I/O — just reads the plan the studio already produced, so the studio
can describe and sanity-check its own output before anyone builds it.
"""
from __future__ import annotations

from typing import Any

from .game_blueprint import group_execution_plan

# Behaviours that give a game something to DO — an objective, a threat, or motion
# the player must react to. A scene with a player but none of these is a sandbox,
# not a game.
INTERACTIVE_BEHAVIOURS = frozenset({
    "goal", "collectible", "killzone", "mover", "follow", "chase", "spawner", "patrol",
})


def summarize_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Count the objects and behaviours a plan will create. Pure.

    Returns {object_count, behaviour_counts}. ``unity_create_primitive`` makes one
    object, ``unity_place_primitives`` makes ``count`` objects; ``unity_set_tag``
    creates nothing. Physics behaviours (``unity_add_gameplay_behaviour``) and
    scripted behaviours (``script_behaviour`` steps) both land in behaviour_counts.
    """
    steps = plan.get("steps", []) if isinstance(plan, dict) else []
    object_count = 0
    behaviour_counts: dict[str, int] = {}
    for step in steps:
        if "tool" in step:
            tool = step.get("tool")
            kw = step.get("kwargs", {}) or {}
            if tool == "unity_create_primitive":
                object_count += 1
            elif tool == "unity_place_primitives":
                object_count += int(kw.get("count", 0) or 0)
            elif tool == "unity_add_gameplay_behaviour":
                b = kw.get("behaviour", "") or ""
                if b:
                    behaviour_counts[b] = behaviour_counts.get(b, 0) + 1
        elif "script_behaviour" in step:
            b = (step["script_behaviour"] or {}).get("behaviour", "") or ""
            if b:
                behaviour_counts[b] = behaviour_counts.get(b, 0) + 1
    return {"object_count": object_count, "behaviour_counts": behaviour_counts}


def assess_game_readiness(plan: dict[str, Any]) -> dict[str, Any]:
    """Analyse a plan and judge whether it is a playable game. Pure, no bridge.

    Returns {ok, game, object_count, behaviour_counts, unique_scripts, has_player,
    has_goal, has_score, collectible_count, hazard_count, playable, warnings}.
    ``playable`` is True when there is a player AND at least one interactive element
    (objective / threat / reactive motion). ``warnings`` lists what is missing.
    """
    steps = plan.get("steps", []) if isinstance(plan, dict) else []
    summary = summarize_plan(plan)
    object_count = summary["object_count"]
    behaviour_counts = summary["behaviour_counts"]
    unique_scripts = len(group_execution_plan(steps)["script_behaviours"])

    has_player = behaviour_counts.get("player", 0) > 0
    has_goal = behaviour_counts.get("goal", 0) > 0
    has_score = behaviour_counts.get("score", 0) > 0
    collectible_count = behaviour_counts.get("collectible", 0)
    hazard_count = behaviour_counts.get("killzone", 0)
    interactive = sum(behaviour_counts.get(b, 0) for b in INTERACTIVE_BEHAVIOURS)
    playable = has_player and interactive > 0

    warnings: list[str] = []
    if object_count == 0:
        warnings.append("empty scene - no objects")
    if not has_player:
        warnings.append("no player - nothing to control")
    if not has_goal:
        warnings.append("no goal - no explicit win condition")
    if collectible_count > 0 and not has_score:
        warnings.append("collectibles but no score HUD")
    if not playable:
        warnings.append("not playable - needs a player plus an interactive element")

    return {
        "ok": True,
        "game": (plan.get("game") or plan.get("decor") or "unknown") if isinstance(plan, dict) else "unknown",
        "object_count": object_count,
        "behaviour_counts": behaviour_counts,
        "unique_scripts": unique_scripts,
        "has_player": has_player,
        "has_goal": has_goal,
        "has_score": has_score,
        "collectible_count": collectible_count,
        "hazard_count": hazard_count,
        "playable": playable,
        "warnings": warnings,
    }
