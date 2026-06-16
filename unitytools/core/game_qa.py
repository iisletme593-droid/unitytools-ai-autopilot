"""Game QA — pure, bridge-free analysis of a blueprint plan.

Given a plan dict from `plan_game`/`plan_*_game`/`plan_ambient_decor` (its `steps`
list), count what the game is made of and judge whether it is actually playable.
No Unity, no I/O — just reads the plan the studio already produced, so the studio
can describe and sanity-check its own output before anyone builds it.
"""
from __future__ import annotations

from typing import Any

from .game_blueprint import group_execution_plan, BLUEPRINTS, plan_game

# Behaviours that give a game something to DO — an objective, a threat, or motion
# the player must react to. A scene with a player but none of these is a sandbox,
# not a game.
INTERACTIVE_BEHAVIOURS = frozenset({
    "goal", "collectible", "killzone", "mover", "follow", "chase", "spawner", "patrol",
    "enemy", "horde",
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

    # a "player" is anything that gives the user a controllable avatar: the WASD
    # `player` controller or the endless-runner's auto-run `runner` controller
    has_player = behaviour_counts.get("player", 0) > 0 or behaviour_counts.get("runner", 0) > 0
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


def summarize_catalog(count: int = 5) -> dict[str, Any]:
    """One-glance "what can I make?" report across the whole game catalog. Pure.

    Walks every blueprint in BLUEPRINTS, plans it at ``count`` and assesses its
    readiness, returning {ok, game_count, games:[...], all_playable,
    unique_behaviours, behaviour_count}. No bridge, no scene changes — the studio
    describing its own capabilities.
    """
    games: list[dict[str, Any]] = []
    behaviours: set[str] = set()
    all_playable = True
    for gt in sorted(BLUEPRINTS):
        plan = plan_game(gt, count)
        report = assess_game_readiness(plan)
        games.append({
            "game_type": gt,
            "summary": plan.get("summary", ""),
            "object_count": report["object_count"],
            "unique_scripts": report["unique_scripts"],
            "playable": report["playable"],
            "has_player": report["has_player"],
            "has_goal": report["has_goal"],
            "has_score": report["has_score"],
            "warnings": report["warnings"],
        })
        behaviours.update(report["behaviour_counts"].keys())
        all_playable = all_playable and report["playable"]
    return {
        "ok": True,
        "game_count": len(games),
        "games": games,
        "all_playable": all_playable,
        "unique_behaviours": sorted(behaviours),
        "behaviour_count": len(behaviours),
    }


def build_game_capabilities_summary() -> str:
    """A compact, CODE-DERIVED block describing the studio's game-making powers,
    for injection into the master planner prompt. Reads summarize_catalog() rather
    than hardcoding, so it stays current as blueprints/behaviours change. Pure.
    """
    cat = summarize_catalog()
    types = ", ".join(g["game_type"] for g in cat["games"])
    lines = [
        "=== GAME STUDIO CAPABILITIES ===",
        f"This studio can author {cat['game_count']} playable game types: {types}.",
        "Route game requests to these tools (deterministic, no guessing):",
        "- Build a game ('... oyunu yap/kur', 'build me a X game', difficulty kolay/orta/zor sets the size,"
        " 'tohum 42'/'seed 42' makes it reproducible) -> unity_build_simple_game(game_type, collectible_count, seed, execute).",
        "- Assess / QA a game ('oyunu degerlendir', 'oynanabilir mi', 'is the game playable')"
        " -> unity_assess_game(game_type).",
        "- Difficulty variations ('varyasyon', 'zorluk secenekleri', 'easy/medium/hard')"
        " -> unity_game_variations(game_type).",
        "- List the catalog ('hangi oyunlar', 'neler yapabilirsin', 'what games') -> unity_game_catalog().",
        "- Save a game to disk ('... olarak kaydet', 'save as X') -> unity_save_game(game_type, name);"
        " load one back ('oyunu yukle X', 'load X') -> unity_load_game(name); list saves"
        " ('kayitli oyunlar', 'saved games') -> unity_list_saved_games().",
        "- Import external game JSON (validated, never trust it) -> unity_import_game(json_text);"
        " build a saved game -> unity_build_loaded_game(name, execute).",
        f"Gameplay behaviours available: {', '.join(cat['unique_behaviours'])}.",
        "execute=False plans only (safe, no scene change); execute=True builds and triggers a Unity recompile.",
    ]
    return "\n".join(lines)
