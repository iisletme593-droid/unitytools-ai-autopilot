"""High-level Unity scene understanding and bulk editing tools."""
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


@tool(description="Build a semantic catalog of all scene GameObjects grouped by category, materials, components, and hierarchy path. Use this before editing unknown scenes.")
def unity_get_scene_catalog(max_results: int = 2000) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call("get_scene_catalog", {"max_results": max_results}, timeout=60)
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find scene objects semantically by name, material, component, hierarchy, and category. Do not rely on tags for user phrases like tree, rock, ground, village, campfire.")
def unity_find_scene_objects_semantic(query: str, category: str = "", max_results: int = 100) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "find_scene_objects_semantic",
            {"query": query, "category": category, "max_results": max_results},
            timeout=60,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Delete scene objects semantically by category/query. Use this for 'remove all trees/rocks/campfires' instead of tag search.")
def unity_delete_scene_objects_semantic(query: str, category: str = "", max: int = 500) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "delete_scene_objects_semantic",
            {"query": query, "category": category, "max": max},
            timeout=90,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Apply a coherent material/color palette to scene objects by semantic category: forest, village, dark_fantasy, ground, rocks, trees, campfire.")
def unity_apply_material_palette(query: str = "", category: str = "", palette: str = "forest", max: int = 2000) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "apply_material_palette",
            {"query": query, "category": category, "palette": palette, "max": max},
            timeout=120,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a complete optimized forest scene in one Unity call: terrain, 80-120 mixed pine/dead trees, rocks, fog, light, camera, names, and materials. Prefer this for large forest prompts to avoid timeouts.")
def unity_create_optimized_forest_scene(
    tree_count: int = 100,
    rock_count: int = 18,
    terrain_size: float = 120.0,
    clear_scene: bool = True,
    seed: int = 12345,
) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "create_optimized_forest_scene",
            {
                "tree_count": tree_count,
                "rock_count": rock_count,
                "terrain_size": terrain_size,
                "clear_scene": clear_scene,
                "seed": seed,
            },
            timeout=180,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Lower Unity editor/rendering cost for heavy scenes: disables expensive shadows, lowers LOD bias and anti-aliasing. Use when Unity is lagging.")
def unity_optimize_editor_performance(shadow_distance: float = 25.0, lod_bias: float = 0.55) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "optimize_editor_performance",
            {"shadow_distance": shadow_distance, "lod_bias": lod_bias},
            timeout=60,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


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
