"""High-level Unity scene understanding and bulk editing tools.

NOTE: the semantic catalog / find / delete / material-palette / repair / forest /
optimize tools that used to live here are now the canonical ones in
``unity_tools.py`` (tested + live-proven). They were duplicated here and silently
shadowed by last-import-wins, so they were removed to end the collision (see
tests/test_no_tool_collisions.py). The richer explicit per-call timeouts those
copies carried can be ported onto the unity_tools versions in a follow-up.

Only the unique ``unity_export_scene_knowledge_base`` remains here.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.tool_registry import tool


_UNITY = None  # type: ignore


def _ensure_unity() -> tuple[bool, str]:
    if _UNITY is None:
        return False, "UnityBridge is not initialized"
    if not _UNITY.is_connected():
        return False, "Could not connect to the Unity Editor"
    return True, ""


@tool(description="Export a deep scene knowledge file listing object names, categories, materials, components, and hierarchy paths so future searches understand the scene.")
def unity_export_scene_knowledge_base(output_relative: str = "AutopilotData/scene_knowledge.md", max_results: int = 5000) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        project = _UNITY.call("get_project_info", {}, timeout=10)
        catalog = _UNITY.call("get_scene_catalog", {"max_results": max_results}, timeout=90)
        data_path = Path(project["data_path"])
        project_root = data_path.parent
        out_path = project_root / output_relative
        out_path.parent.mkdir(parents=True, exist_ok=True)
        groups = catalog.get("groups", {}) if isinstance(catalog, dict) else {}
        objects = catalog.get("objects", []) if isinstance(catalog, dict) else []
        lines = [
            "# Unity Scene Knowledge Base",
            "",
            f"Scene: {catalog.get('scene') if isinstance(catalog, dict) else ''}",
            f"Total objects: {catalog.get('total_objects') if isinstance(catalog, dict) else ''}",
            "",
            "## Groups",
        ]
        for name, count in groups.items():
            lines.append(f"- {name}: {count}")
        lines.extend(["", "## Objects"])
        for obj in objects:
            mats = ", ".join(obj.get("materials", []) or [])
            comps = ", ".join(obj.get("components", []) or [])
            lines.append(
                f"- [{obj.get('category', 'other')}] {obj.get('path', obj.get('name'))} | "
                f"materials: {mats or '-'} | components: {comps or '-'}"
            )
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        json_path = out_path.with_suffix(".json")
        json_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        return {
            "ok": True,
            "markdown_path": str(out_path),
            "json_path": str(json_path),
            "groups": groups,
            "object_count": len(objects),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
