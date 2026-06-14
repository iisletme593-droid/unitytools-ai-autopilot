"""Safety policy for autopilot tool execution.

The autopilot can call scene-destroying tools (delete, wipe-and-regenerate,
material/LOD rewrites). Before the FIRST such call in a turn the orchestrator
auto-saves a scene snapshot so the user can roll back with
``unity_restore_scene_snapshot``.

This module is pure policy (no Unity, no I/O); the orchestrator wires it into its
single tool-execution path (``Orchestrator._execute_tool``).
"""
from __future__ import annotations

# Tools that overwrite or destroy existing scene content (snapshot-worthy).
# Additive authoring (placing primitives, building structures) is intentionally
# NOT here -- a snapshot before every create would be noise.
DESTRUCTIVE_TOOLS = frozenset({
    "unity_delete_object",
    "unity_delete_scene_objects_semantic",
    "unity_create_optimized_forest_scene",  # clear_scene=True wipes the scene
    "unity_apply_lod_decimation_plan",       # mutates / replaces meshes
    "unity_apply_material_palette",          # rewrites scene materials
    "unity_repair_material_issues",          # recreates scene materials
})


def is_destructive(tool_name: str) -> bool:
    """True when calling ``tool_name`` overwrites/destroys scene content."""
    return tool_name in DESTRUCTIVE_TOOLS


def snapshot_label_for(tool_name: str) -> str:
    """A filesystem-safe snapshot label describing what we are guarding against."""
    base = tool_name[len("unity_"):] if tool_name.startswith("unity_") else tool_name
    base = "".join(ch if ch.isalnum() else "_" for ch in base).strip("_")[:40]
    return f"auto_before_{base or 'mutate'}"
