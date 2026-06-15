"""Game I/O — serialize a game/decor plan to JSON and back (P8: save/load).

The first step toward game persistence: a plan produced by `plan_game` /
`plan_*_game` / `plan_ambient_decor` can be turned into a stable, versioned JSON
string and parsed back into the exact same plan. Pure string<->dict transforms —
no disk, no bridge, no scene changes — so a saved game can be stored, shared,
versioned, diffed, or replayed later.
"""
from __future__ import annotations

import json
from typing import Any

SCHEMA = "unitytools.game_plan"
SCHEMA_VERSION = 1


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
