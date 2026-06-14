"""Visual-QA assessment: turn a ``run_visual_qa`` result into a pass/fix plan.

Pure, GPU-free, deterministic. This is the mechanical half of the
build -> QA -> fix loop (the "learning / focus" kernel): given the editor's
visual-QA verdict, decide whether the scene passes and, if not, which *existing*
repair tools to run -- without burning an LLM round-trip on the bookkeeping.

The autopilot tool ``unity_quality_pass`` drives the actual loop on top of this.
"""
from __future__ import annotations

from typing import Any


def _int(d: dict[str, Any], key: str) -> int:
    try:
        return int(d.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def assess_qa(qa: dict[str, Any] | None) -> dict[str, Any]:
    """Assess a ``run_visual_qa`` result.

    Returns a dict with:
      * ``passed``  -- True when there is nothing left to auto-fix
      * ``score``   -- 0..100 quality heuristic (materials weighted hardest)
      * ``fixes``   -- ordered concrete tool actions, e.g.
                       ``{"tool": "unity_repair_material_issues", "params": {...}}``
      * ``notes``   -- non-actionable observations (empty scene, no camera)
      * ``issues``  -- the editor's own issue strings, passed through
      * ``counts``  -- the normalized counts used for the decision
    """
    qa = qa or {}
    counts = qa.get("counts") or {}
    missing = _int(counts, "missing_materials")
    broken = _int(counts, "broken_materials")
    unsupported = _int(counts, "unsupported_materials")
    lights = _int(counts, "lights")
    cameras = _int(counts, "cameras")
    renderers = _int(counts, "renderers")
    objects = _int(counts, "objects")

    fixes: list[dict[str, Any]] = []
    if missing or broken:
        fixes.append({
            "tool": "unity_repair_material_issues",
            "params": {"include_unsupported": bool(unsupported)},
            "reason": f"{missing} missing / {broken} broken materials",
        })
    elif unsupported:
        fixes.append({
            "tool": "unity_repair_material_issues",
            "params": {"include_unsupported": True},
            "reason": f"{unsupported} unsupported materials",
        })
    # Only suggest lighting when there is geometry to light.
    if renderers > 0 and lights == 0:
        fixes.append({
            "tool": "unity_setup_studio_lighting",
            "params": {},
            "reason": "scene has geometry but no lights",
        })

    notes: list[str] = []
    if objects == 0 or renderers == 0:
        notes.append("scene looks empty (no renderers)")
    if cameras == 0:
        notes.append("no camera in scene")

    score = 100
    score -= 8 * (missing + broken)
    score -= 3 * unsupported
    if renderers > 0 and lights == 0:
        score -= 15
    if renderers == 0:
        score -= 20
    score = max(0, min(100, score))

    return {
        "passed": not fixes,
        "score": score,
        "fixes": fixes,
        "notes": notes,
        "issues": list(qa.get("issues") or []),
        "counts": {
            "missing_materials": missing,
            "broken_materials": broken,
            "unsupported_materials": unsupported,
            "lights": lights,
            "cameras": cameras,
            "renderers": renderers,
            "objects": objects,
        },
    }
