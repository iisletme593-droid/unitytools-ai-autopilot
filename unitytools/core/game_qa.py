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
    "enemy", "horde", "pushable", "holdzone", "boss",
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


def critique_design(behaviour_counts: dict[str, int]) -> list[str]:
    """An HONEST design critique derived purely from the plan's behaviour counts --
    no simulation, no faked playtest. It flags coherence/balance gaps that a plan can
    have even while being structurally "playable": a fight with no lose condition, a
    win/lose manager with no way to win, a countdown you can't actually lose, an attack
    with nothing to hit. Returns a list of plain-language notes (empty == no issues
    found). The same reasoning the studio would use to review its own output.
    """
    c = behaviour_counts.get
    enemy, health, attack = c("enemy", 0), c("health", 0), c("attack", 0)
    timer, gameover, ranged = c("timer", 0), c("gameover", 0), c("ranged", 0)
    goal, holdzone = c("goal", 0), c("holdzone", 0)
    # a "foe" is anything the player must defeat to win: the small `enemy` AI OR a high-HP
    # `boss`. Counting both keeps the combat critique honest for a boss-only duel (no `enemy`).
    foes = enemy + c("boss", 0)
    notes: list[str] = []

    if foes > 0 and health == 0:
        notes.append("enemies are present but nothing has health, so the player cannot be "
                     "defeated -- the fight has no lose condition")
    if foes > 0 and attack == 0 and ranged == 0 and goal == 0 and holdzone == 0:
        # "no attack" is only a flaw when there is NO non-combat way to win; a goal to
        # reach or a zone to hold makes avoiding the enemies the intended play
        notes.append("the player faces enemies but has no attack, so they can only flee -- "
                     "combat is one-sided")
    if attack > 0 and foes == 0:
        notes.append("the player can attack but there are no enemies to fight")
    if ranged > 0 and foes == 0:
        notes.append("a ranged attacker has no enemies in range to target")
    if gameover > 0 and foes == 0 and timer == 0 and goal == 0 and c("collectrace", 0) == 0:
        notes.append("the win/lose manager has no WIN trigger (no enemies to clear, no "
                     "survival timer, no goal to reach) -- the game can only be lost")
    if timer > 0 and (foes == 0 or health == 0):
        notes.append("the countdown can be outlasted but there is no combat lose path -- the "
                     "game cannot actually be lost")
    return notes


def assess_game_readiness(plan: dict[str, Any]) -> dict[str, Any]:
    """Analyse a plan and judge whether it is a playable game. Pure, no bridge.

    Returns {ok, game, object_count, behaviour_counts, unique_scripts, has_player,
    has_goal, has_score, collectible_count, hazard_count, playable, warnings,
    design_notes}. ``playable`` is True when there is a player AND at least one
    interactive element (objective / threat / reactive motion). ``warnings`` lists
    structural gaps; ``design_notes`` is the deeper design critique (see
    ``critique_design``) -- coherence issues a structurally-playable game can still have.
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
        "design_notes": critique_design(behaviour_counts),
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


# Scripted-behaviour categories (canonical behaviour -> human category). VALIDATED
# against the live _SCRIPT_TEMPLATES by test_studio_report so it cannot drift: every
# unique MonoBehaviour class must fall under exactly one category. Add a new behaviour
# and the drift test fails until it is categorized here -- the report stays honest.
_BEHAVIOUR_CATEGORIES: dict[str, list[str]] = {
    "control": ["player", "runner"],
    "movement": ["rotate", "move", "bob", "bounce", "patrol", "follow", "orbit", "wander"],
    "world": ["collectible", "goal", "killzone", "spawner", "detector", "pushable", "puzzle", "holdzone", "escort"],
    "combat": ["health", "attack", "enemy", "ranged", "reward", "horde", "boss"],
    "progression": ["xp", "loot", "inventory", "score"],
    "game feel": ["title", "gameover", "sound", "timer", "collectrace"],
}

# Game-feel behaviours whose presence-per-game the report surfaces.
_FEEL_BEHAVIOURS = ("title", "gameover", "sound")


def _games_with_behaviour(behaviour: str, count: int = 4) -> list[str]:
    """Which game types include ``behaviour`` in their plan (code-derived). Pure."""
    out: list[str] = []
    for gt in sorted(BLUEPRINTS):
        behs = {s["script_behaviour"]["behaviour"]
                for s in plan_game(gt, count).get("steps", [])
                if "script_behaviour" in s}
        if behaviour in behs:
            out.append(gt)
    return out


def _registered_tool_names() -> list[str]:
    """Names of all registered @tool tools (lazy import; [] if none registered)."""
    try:
        from .tool_registry import get_all_tools
        return sorted(t.name for t in get_all_tools())
    except Exception:
        return []


def studio_health(count: int = 4) -> dict[str, Any]:
    """A CODE-DERIVED self-audit of the whole catalog: build every blueprint and check
    it is VALID (whitelisted tools, no traversal), PLAYABLE (player + interactive), and
    COHERENT (no design-critique notes). Pure; the studio auditing its own output, the
    same checks a human reviewer would run. Returns {ok, game_count, all_valid,
    all_playable, all_coherent, games:[...], flagged:[...]} -- flagged is empty when
    every game is clean.
    """
    from .game_io import validate_plan                       # lazy: avoids an import cycle
    games: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    all_valid = all_playable = all_coherent = True
    for gt in sorted(BLUEPRINTS):
        plan = plan_game(gt, count)
        report = assess_game_readiness(plan)
        valid = bool(validate_plan(plan)["ok"])
        playable = bool(report["playable"])
        notes = report["design_notes"]
        coherent = not notes
        games.append({"game_type": gt, "valid": valid, "playable": playable,
                      "coherent": coherent, "design_notes": notes})
        all_valid = all_valid and valid
        all_playable = all_playable and playable
        all_coherent = all_coherent and coherent
        if not (valid and playable and coherent):
            flagged.append({"game_type": gt, "valid": valid, "playable": playable,
                            "design_notes": notes})
    return {"ok": True, "game_count": len(games), "all_valid": all_valid,
            "all_playable": all_playable, "all_coherent": all_coherent,
            "games": games, "flagged": flagged}


# a representative matrix of composer specs (each element on its own + a few mixes);
# the couplings should make every one valid + playable + coherent.
_COMPOSE_HEALTH_SPECS = [
    {"enemy": 4}, {"collectible": 5}, {"hazard": 4}, {"spawner": 3}, {"guard": 3},
    {"crate": 3}, {"goal": True, "collectible": 3}, {"enemy": 3, "timer": True},
    {"enemy": 3, "collectible": 3, "ranged": True}, {"enemy": 2, "crate": 2, "guard": 2},
    {"moving_hazard": 4}, {"moving_hazard": 3, "collectible": 3, "goal": True},
]


def compose_health() -> dict[str, Any]:
    """A CODE-DERIVED self-audit of the freeform COMPOSER: compose a representative
    matrix of element specs (each type alone + a few mixes) and check each is VALID +
    PLAYABLE + COHERENT. A regression guard for the composer's couplings (enemy ->
    health+attack, guard -> goal, crate -> puzzle, ...). Pure. Returns {ok, case_count,
    all_valid, all_playable, all_coherent, cases:[...], flagged:[...]}.
    """
    from .game_blueprint import compose_custom_game
    from .game_io import validate_plan
    cases: list[dict[str, Any]] = []
    flagged: list[dict[str, Any]] = []
    all_valid = all_playable = all_coherent = True
    for spec in _COMPOSE_HEALTH_SPECS:
        plan = compose_custom_game(**spec)
        report = assess_game_readiness(plan)
        valid = bool(validate_plan(plan)["ok"])
        playable = bool(report["playable"])
        notes = report["design_notes"]
        coherent = not notes
        cases.append({"spec": spec, "valid": valid, "playable": playable,
                      "coherent": coherent, "design_notes": notes})
        all_valid = all_valid and valid
        all_playable = all_playable and playable
        all_coherent = all_coherent and coherent
        if not (valid and playable and coherent):
            flagged.append({"spec": spec, "valid": valid, "playable": playable, "design_notes": notes})
    return {"ok": True, "case_count": len(cases), "all_valid": all_valid,
            "all_playable": all_playable, "all_coherent": all_coherent,
            "cases": cases, "flagged": flagged}


def build_studio_report() -> str:
    """A comprehensive, user-facing, CODE-DERIVED studio report (markdown string).

    Everything is computed from the live registries (BLUEPRINTS, the scripted-template
    and physics behaviour catalogs, the tool registry), so the report can never drift
    from what the studio can actually do. Pure ASCII; reads only (no bridge, no I/O).
    """
    from .gameplay import _SCRIPT_TEMPLATES, GAMEPLAY_BEHAVIOURS

    cat = summarize_catalog()
    unique_classes = {v[0] for v in _SCRIPT_TEMPLATES.values()}

    lines = ["# Unity Autopilot -- Game Studio Report", ""]
    lines.append("Turns a natural-language request (Turkish or English) into a playable Unity scene. "
                 "This report is generated entirely from the live code, so it never drifts.")
    lines.append("")

    # (a) game types + their (code-derived) one-line summaries
    lines.append(f"## Game types ({cat['game_count']})")
    for g in cat["games"]:
        lines.append(f"- `{g['game_type']}` -- {g['summary']}")
    lines.append("")

    # (a2) self-audit: every blueprint AND a matrix of composed games must be valid +
    # playable + coherent
    health = studio_health()
    comp = compose_health()
    ok = (health["all_valid"] and health["all_playable"] and health["all_coherent"]
          and comp["all_valid"] and comp["all_playable"] and comp["all_coherent"])
    if ok:
        lines.append(f"## Studio health: OK ({health['game_count']}/{health['game_count']} game types, "
                     f"{comp['case_count']}/{comp['case_count']} composer cases)")
        lines.append("Every game type and a representative matrix of composed games build valid "
                     "(whitelisted tools, no traversal), playable (a player + something to do), and "
                     "coherent (pass the design critique).")
    else:
        lines.append("## Studio health: NEEDS ATTENTION")
        for f in health["flagged"]:
            issues = []
            if not f["valid"]:
                issues.append("invalid")
            if not f["playable"]:
                issues.append("not playable")
            if f["design_notes"]:
                issues.append("; ".join(f["design_notes"]))
            lines.append(f"- `{f['game_type']}`: {', '.join(issues)}")
        for f in comp["flagged"]:
            lines.append(f"- composer {f['spec']}: "
                         f"{'; '.join(f['design_notes']) if f['design_notes'] else 'invalid/not playable'}")
    lines.append("")

    # (b) behaviour catalog, categorized (scripted MonoBehaviours + physics primitives)
    n_scripted = len(unique_classes)
    n_physics = len(GAMEPLAY_BEHAVIOURS)
    lines.append(f"## Behaviour catalog ({n_scripted} scripted MonoBehaviours + {n_physics} physics primitives)")
    for category, behs in _BEHAVIOUR_CATEGORIES.items():
        classes = {_SCRIPT_TEMPLATES[b][0] for b in behs}
        lines.append(f"- **{category}** ({len(classes)}): {', '.join(behs)}")
    lines.append(f"- **physics** ({n_physics}): {', '.join(sorted(GAMEPLAY_BEHAVIOURS))}")
    lines.append("")

    # (c) game feel -- which games actually wire in title / win-lose / sound
    lines.append("## Game feel (title screen, win/lose, sound cue)")
    for feel in _FEEL_BEHAVIOURS:
        games = _games_with_behaviour(feel)
        where = ", ".join(games) if games else "(available, not yet wired into a blueprint)"
        lines.append(f"- {feel}: {where}")
    lines.append("")

    # (c2) freeform composition -- beyond the presets (only if the tool is registered)
    if "unity_compose_game" in _registered_tool_names():
        lines.append("## Custom composition")
        lines.append("Beyond the fixed game types, describe an element mix ('a player, 5 enemies, 3 "
                     "collectibles, a timer') and the studio composes a valid, playable plan from the "
                     "same building blocks (unity_compose_game) -- enemies pull in health/attack + a "
                     "win/lose manager, a timer makes it outlast-the-clock.")
        lines.append("")

    # (d) persistence
    lines.append("## Persistence")
    lines.append("Games save/load to disk as validated JSON (path-traversal-guarded, tool-whitelisted): "
                 "unity_save_game, unity_load_game, unity_list_saved_games, unity_import_game, "
                 "unity_build_loaded_game.")
    lines.append("")

    # (e) procedural & deterministic
    lines.append("## Procedural & deterministic")
    lines.append("Seeded layouts (same seed -> same scene) and always-solvable procedural mazes; every "
                 "generator is deterministic (no Math.random, no time-of-day), so a build is reproducible.")
    lines.append("")

    # (f) tools (live count from the registry)
    tool_names = _registered_tool_names()
    if tool_names:
        game_tools = sorted(t for t in tool_names
                            if "game" in t or t in ("unity_animate_group", "unity_studio_report",
                                                    "unity_plan_campaign"))
        lines.append(f"## Tools ({len(tool_names)} registered)")
        lines.append("Game-studio tools: " + ", ".join(game_tools) + ".")
        lines.append("")

    lines.append("execute=False plans only (safe, no scene change); execute=True builds and triggers "
                 "a Unity recompile.")
    return "\n".join(lines)


# --- the game showcase: "say this -> get this game" -------------------------
# A curated (example NL prompt, one-line pitch) per game type. The example is VERIFIED
# (live, by showcase_routing + a test) to actually route to that game's build, so the
# showcase is a self-checking discovery surface, not hand-waved claims. Guarded by a test
# that every BLUEPRINTS type has an entry, so a new game type forces an example here.
_GAME_EXAMPLES: dict[str, tuple[str, str]] = {
    "collectathon": ("toplama oyunu yap", "grab every pickup and reach the goal"),
    "dodge": ("dodge oyunu kur", "weave through moving hazards to the exit"),
    "survival": ("hayatta kalma oyunu kur", "endure spawners raining hazards"),
    "platformer": ("platformer oyunu kur", "jump up the platforms to a goal on top"),
    "chase": ("kovalamaca oyunu kur", "outrun the enemies hunting you while you grab loot"),
    "maze": ("labirent oyunu kur", "escape a procedurally generated labyrinth"),
    "arena": ("arena oyunu kur", "an armed brawl against a ring of enemies"),
    "horde": ("horde oyunu kur", "survive escalating waves from a central spawner"),
    "runner": ("runner oyunu kur", "an endless runner -- strafe and jump for distance"),
    "tower_defense": ("tower defense oyunu kur", "towers + a hero defend a base from a march of enemies"),
    "time_survival": ("zamana karsi hayatta kalma oyunu kur", "outlast the countdown in a fight"),
    "stealth": ("stealth oyunu kur", "slip past patrolling guards to the exit unseen"),
    "puzzle": ("puzzle oyunu kur", "push every crate onto a target (sokoban)"),
    "hold": ("king of the hill oyunu kur", "hold a zone under pressure (king of the hill)"),
    "escort": ("escort oyunu kur", "guide and protect a moving VIP to the goal"),
    "boss": ("boss arena oyunu kur", "duel a high-HP boss with a melee + ranged kit"),
    "collector_race": ("toplama yarisi yap", "collect everything before the clock runs out"),
}


def showcase_routing() -> dict[str, Any]:
    """Verify (live) that each game type's curated example prompt routes to its build. Pure
    aside from a lazy import of the intent planner. Returns {ok, all_route, rows:[{game_type,
    prompt, routes_to, builds}]} -- ``builds`` is True iff the example plans
    unity_build_simple_game for exactly that game_type. A regression guard for the WHOLE
    NL-intent layer: break any game's detection and this (and its test) goes red.
    """
    from .game_studio_actions import plan_unity_fast_action      # lazy: avoid an import cycle
    rows: list[dict[str, Any]] = []
    all_route = True
    for gt in sorted(BLUEPRINTS):
        prompt = _GAME_EXAMPLES.get(gt, (f"{gt} oyunu kur", ""))[0]
        steps = plan_unity_fast_action(prompt).get("steps", [])
        step = steps[0] if steps else {}
        builds = (step.get("tool") == "unity_build_simple_game"
                  and step.get("kwargs", {}).get("game_type") == gt)
        rows.append({"game_type": gt, "prompt": prompt, "routes_to": step.get("tool"), "builds": builds})
        all_route = all_route and builds
    return {"ok": True, "all_route": all_route, "rows": rows}


def build_game_showcase() -> str:
    """A user-facing, CODE-DERIVED showcase: for every game type, the example NL prompt that
    builds it (routing verified live), a one-line pitch, and its size. Pure ASCII markdown;
    reads only (no bridge, no I/O). The discovery counterpart to the studio report.
    """
    route = showcase_routing()
    verified = sum(1 for r in route["rows"] if r["builds"])
    lines = ["# Unity Autopilot -- Game Showcase", ""]
    lines.append("Say the prompt, get the game. Every example below is verified (live) to route to its "
                 "game type, and the counts are code-derived, so this never drifts.")
    lines.append("")
    lines.append(f"## {len(route['rows'])} games -- say it, play it")
    for gt in sorted(BLUEPRINTS):
        prompt, pitch = _GAME_EXAMPLES.get(gt, (f"{gt} oyunu kur", ""))
        report = assess_game_readiness(plan_game(gt, 4))
        lines.append(f"- `{gt}` -- say \"{prompt}\" -> {pitch} ({report['object_count']} objects).")
    lines.append("")
    status = "all routing OK" if route["all_route"] else "SOME EXAMPLES DO NOT ROUTE"
    lines.append(f"Routing self-check: {status} ({verified}/{len(route['rows'])} examples verified to build "
                 "their game type).")
    return "\n".join(lines)
