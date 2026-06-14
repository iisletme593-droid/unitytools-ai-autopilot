"""Gameplay behaviour catalog — the first step from "scene decorator" to
"game maker".

Each behaviour composes EXISTING, configurable bridge tools (Rigidbody via
set_rigidbody, colliders via add_collider) into a real gameplay primitive, so the
autopilot can give an object physics with no new C# code. Behaviours that need a
custom MonoBehaviour (rotate/patrol/follow) are listed in NEEDS_SCRIPT and reported
as not-yet-supported — they await a future `add_script_behaviour` bridge command
rather than silently failing.

Pure data + planning here; the unity_add_gameplay_behaviour tool executes the plan.
"""
from __future__ import annotations

from typing import Any

# behaviour -> ordered (tool_name, extra_kwargs) steps. "name" is injected later.
GAMEPLAY_BEHAVIOURS: dict[str, list[tuple[str, dict[str, Any]]]] = {
    # gravity-driven rigid body that collides with the world
    "physics": [
        ("unity_set_rigidbody", {"use_gravity": True}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    "falling": [
        ("unity_set_rigidbody", {"use_gravity": True}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    "heavy": [
        ("unity_set_rigidbody", {"use_gravity": True, "mass": 10.0}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    "floaty": [
        ("unity_set_rigidbody", {"use_gravity": True, "drag": 4.0}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    # script-driven movement without physics gravity (e.g. a moving platform)
    "kinematic": [
        ("unity_set_rigidbody", {"is_kinematic": True, "use_gravity": False}),
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
    # solid, non-moving obstacle (collider only, no rigidbody)
    "static_obstacle": [
        ("unity_add_collider", {"collider_type": "Box"}),
    ],
}

# Behaviours that genuinely need a custom MonoBehaviour script. Honestly flagged
# instead of faked; unlocked by a future add_script_behaviour bridge command.
NEEDS_SCRIPT: frozenset[str] = frozenset({
    "rotate", "spin", "spinner", "patrol", "follow", "chase", "orbit",
    "move", "bob", "bounce", "wander",
})

# friendly aliases (incl. Turkish)
_ALIASES = {
    "fall": "falling", "dus": "falling", "dusen": "falling",
    "fizik": "physics", "agir": "heavy", "hafif": "floaty",
    "engel": "static_obstacle", "obstacle": "static_obstacle", "solid": "static_obstacle",
    "platform": "kinematic",
    "don": "rotate", "donen": "rotate", "donder": "rotate",
    "hareket": "move", "takip": "follow", "devriye": "patrol", "zipla": "bounce",
}


def normalize_behaviour(behaviour: str) -> str:
    b = (behaviour or "").strip().lower()
    return _ALIASES.get(b, b)


def plan_gameplay_behaviour(behaviour: str, object_name: str) -> dict[str, Any]:
    """Plan the tool steps for a gameplay behaviour on ``object_name``.

    Returns {ok, behaviour, steps:[{tool, kwargs}]} on success; otherwise
    {ok: False, error, ...} (with needs_script=True for script-only behaviours).
    """
    b = normalize_behaviour(behaviour)
    if not object_name:
        return {"ok": False, "error": "object_name is required", "behaviour": b}
    if b in NEEDS_SCRIPT:
        return {
            "ok": False,
            "behaviour": b,
            "needs_script": True,
            "error": f"'{b}' needs a MonoBehaviour script (future add_script_behaviour bridge command)",
        }
    steps = GAMEPLAY_BEHAVIOURS.get(b)
    if steps is None:
        return {
            "ok": False,
            "behaviour": b,
            "error": f"unknown gameplay behaviour: {behaviour!r}",
            "available": sorted(GAMEPLAY_BEHAVIOURS),
        }
    plan = [{"tool": tool, "kwargs": {"name": object_name, **kw}} for tool, kw in steps]
    return {"ok": True, "behaviour": b, "steps": plan}


def _is_collider(component_name: Any) -> bool:
    return str(component_name).endswith("Collider")


def prune_redundant_steps(
    steps: list[dict[str, Any]], existing_components: list[str] | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Drop steps that would duplicate what the object already has.

    Currently: skip an ``unity_add_collider`` step when the object already carries
    a collider (Cube/Sphere primitives ship one), so the behaviour is idempotent.
    Returns (kept_steps, skipped_steps).
    """
    has_collider = any(_is_collider(c) for c in (existing_components or []))
    kept: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for step in steps:
        if step.get("tool") == "unity_add_collider" and has_collider:
            skipped.append({**step, "reason": "object already has a collider"})
        else:
            kept.append(step)
    return kept, skipped
