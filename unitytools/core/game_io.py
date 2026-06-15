"""Game I/O — serialize a game/decor plan to JSON and back (P8: save/load).

The first step toward game persistence: a plan produced by `plan_game` /
`plan_*_game` / `plan_ambient_decor` can be turned into a stable, versioned JSON
string and parsed back into the exact same plan. Pure string<->dict transforms —
no disk, no bridge, no scene changes — so a saved game can be stored, shared,
versioned, diffed, or replayed later.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .security import safe_contained_path

SCHEMA = "unitytools.game_plan"
SCHEMA_VERSION = 1

DEFAULT_GAMES_DIRNAME = ".unitytools/games"
_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9_-]")


def _kind_of(plan: dict[str, Any]) -> str:
    if "game" in plan:
        return "game"
    if "decor" in plan:
        return "decor"
    return "plan"


def serialize_plan(plan: dict[str, Any], *, pretty: bool = False) -> str:
    """Serialize a plan to a versioned JSON envelope string. Deterministic.

    The envelope records the schema, version, kind (game/decor/plan), a name and
    the step count alongside the full plan, so a reader can identify a saved file
    without parsing the whole thing. ``pretty`` indents for human-readable files.
    """
    if not isinstance(plan, dict) or "steps" not in plan:
        raise ValueError("serialize_plan needs a plan dict with a 'steps' list")
    envelope = {
        "schema": SCHEMA,
        "version": SCHEMA_VERSION,
        "kind": _kind_of(plan),
        "name": plan.get("game") or plan.get("decor") or "plan",
        "step_count": len(plan.get("steps") or []),
        "plan": plan,
    }
    return json.dumps(envelope, ensure_ascii=False, sort_keys=True,
                      indent=2 if pretty else None)


def deserialize_plan(text: str) -> dict[str, Any]:
    """Parse a serialized plan envelope back into the plan dict.

    Raises ValueError on anything that is not a valid unitytools game-plan
    envelope (bad JSON, wrong schema, missing/!malformed plan). The returned plan
    equals the original that was serialized (round-trip safe).
    """
    try:
        envelope = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"invalid plan JSON: {exc}") from exc
    if not isinstance(envelope, dict) or envelope.get("schema") != SCHEMA:
        raise ValueError("not a unitytools game-plan envelope")
    if int(envelope.get("version", 0)) > SCHEMA_VERSION:
        raise ValueError(f"plan version {envelope.get('version')} is newer than supported {SCHEMA_VERSION}")
    plan = envelope.get("plan")
    if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list):
        raise ValueError("envelope has no valid plan with a steps list")
    return plan


# Tools a plan is allowed to invoke when built. An external/loaded plan must use
# ONLY these — anything else is rejected so a tampered or hostile JSON file can't
# make the studio call an arbitrary tool. Keep in sync with what the blueprints
# emit (geometry + tag + physics behaviour); scripted behaviours go through
# script_behaviour steps, validated against the template registry.
ALLOWED_PLAN_TOOLS = frozenset({
    "unity_create_primitive",
    "unity_place_primitives",
    "unity_set_tag",
    "unity_add_gameplay_behaviour",
})

_PRIMITIVE = (str, int, float, bool)


def validate_plan(plan: Any, *, max_steps: int = 5000) -> dict[str, Any]:
    """Validate that a (possibly EXTERNAL) plan is structurally safe to build.

    Every step must be exactly one of: a whitelisted ``tool`` call with a flat
    ``kwargs`` dict of primitives, or a ``script_behaviour`` naming a real
    templated behaviour. Returns {ok: True, step_count} or {ok: False, error,
    index?} on the first problem. Pure — never builds anything. Treats the plan as
    untrusted input: do not pass it to the executor until this returns ok.
    """
    if not isinstance(plan, dict):
        return {"ok": False, "error": "plan is not an object"}
    steps = plan.get("steps")
    if not isinstance(steps, list):
        return {"ok": False, "error": "plan has no steps list"}
    if len(steps) > max_steps:
        return {"ok": False, "error": f"too many steps ({len(steps)} > {max_steps})"}

    from .gameplay import generate_behaviour_script

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return {"ok": False, "error": "step is not an object", "index": i}
        has_tool = "tool" in step
        has_sb = "script_behaviour" in step
        if has_tool == has_sb:  # need exactly one
            return {"ok": False, "error": "step must have exactly one of tool/script_behaviour", "index": i}
        if has_tool:
            tool = step.get("tool")
            if tool not in ALLOWED_PLAN_TOOLS:
                return {"ok": False, "error": f"tool not allowed: {tool!r}", "index": i}
            kwargs = step.get("kwargs", {})
            if not isinstance(kwargs, dict):
                return {"ok": False, "error": "kwargs must be an object", "index": i}
            for k, v in kwargs.items():
                if not isinstance(k, str) or not isinstance(v, _PRIMITIVE):
                    return {"ok": False, "error": f"kwargs must be flat str->primitive (bad entry {k!r})", "index": i}
        else:
            sb = step.get("script_behaviour")
            if not isinstance(sb, dict) or not isinstance(sb.get("object"), str) or not isinstance(sb.get("behaviour"), str):
                return {"ok": False, "error": "script_behaviour needs string object + behaviour", "index": i}
            if not generate_behaviour_script(sb["behaviour"]).get("ok"):
                return {"ok": False, "error": f"unknown behaviour: {sb['behaviour']!r}", "index": i}
    return {"ok": True, "step_count": len(steps)}


def plan_metadata(text: str) -> dict[str, Any]:
    """Read just the envelope metadata (schema/version/kind/name/step_count) without
    returning the full plan. Raises ValueError if the text is not a valid envelope.
    """
    try:
        envelope = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"invalid plan JSON: {exc}") from exc
    if not isinstance(envelope, dict) or envelope.get("schema") != SCHEMA:
        raise ValueError("not a unitytools game-plan envelope")
    return {
        "schema": envelope.get("schema"),
        "version": envelope.get("version"),
        "kind": envelope.get("kind"),
        "name": envelope.get("name"),
        "step_count": envelope.get("step_count"),
    }


# --- disk save / load (P8 step 2) ------------------------------------------
# Games are written as JSON under a contained directory. Two layers of defense
# against path traversal: the name is sanitized to a slug (alnum/-/_ only), AND
# the final path is re-checked with safe_contained_path so it can never escape
# the games root. Saving never touches the Unity scene; loading only returns a
# plan (it does not execute it).

def sanitize_game_name(name: str) -> str:
    """Reduce a name to a safe filename slug (A-Z a-z 0-9 _ -), capped at 64 chars.

    Every other character (including '.', '/', '\\') becomes '_', then leading and
    trailing '.'/'_' are stripped. Raises ValueError if nothing safe remains, so a
    name like '../..' cannot produce an empty or traversing filename.
    """
    slug = _UNSAFE_NAME.sub("_", str(name or "").strip())
    slug = slug.strip("._")
    if not slug:
        raise ValueError("invalid game name (need at least one letter/number/-/_)")
    return slug[:64]


def default_games_dir() -> Path:
    """The saved-games directory: env UNITYTOOLS_GAMES_DIR, else .unitytools/games."""
    env = os.getenv("UNITYTOOLS_GAMES_DIR")
    return Path(env) if env else Path.cwd() / DEFAULT_GAMES_DIRNAME


def save_plan_to_file(plan: dict[str, Any], name: str, root: "Path | str | None" = None) -> dict[str, Any]:
    """Serialize ``plan`` and write it to ``<root>/<sanitized name>.json``.

    The path is guarded twice (sanitize + safe_contained_path). Creates the games
    directory if needed. Returns {ok, name, path, step_count}. Does not touch the
    scene.
    """
    games_root = Path(root) if root is not None else default_games_dir()
    slug = sanitize_game_name(name)
    target = safe_contained_path(games_root, slug + ".json")   # raises on escape
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(serialize_plan(plan, pretty=True), encoding="utf-8")
    return {"ok": True, "name": slug, "path": str(target), "step_count": len(plan.get("steps") or [])}


def load_plan_from_file(name: str, root: "Path | str | None" = None) -> dict[str, Any]:
    """Load and parse a saved game by name. Raises ValueError (bad name/content) or
    FileNotFoundError (no such save). Returns the plan dict (not executed).
    """
    games_root = Path(root) if root is not None else default_games_dir()
    slug = sanitize_game_name(name)
    target = safe_contained_path(games_root, slug + ".json")   # raises on escape
    if not target.is_file():
        raise FileNotFoundError(f"no saved game named {slug!r}")
    return deserialize_plan(target.read_text(encoding="utf-8"))


def list_saved_games(root: "Path | str | None" = None) -> list[str]:
    """List saved game names (sorted) under the games directory. Empty if none."""
    games_root = Path(root) if root is not None else default_games_dir()
    if not games_root.is_dir():
        return []
    return sorted(p.stem for p in games_root.glob("*.json") if p.is_file())
