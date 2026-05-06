"""Autopilot quality, planning, memory, and safety tools for Unity workflows."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.tool_registry import tool
from . import asset_tools


_UNITY = None  # type: ignore

_SAFETY_MODES = {"safe", "edit", "destructive"}
_CATEGORY_QUERIES: dict[str, str] = {
    "tree": "tree pine fir forest dead tree trunk foliage",
    "rock": "rock stone boulder cliff moss",
    "grass": "grass bush shrub fern plant flower foliage",
    "building": "building house hut village castle tower wall ruin",
    "prop": "prop barrel crate chest lantern torch campfire table chair",
    "character": "character enemy warrior mage archer ninja shaman humanoid",
    "weapon": "weapon sword axe bow staff shield spear dagger",
    "armor": "armor helmet glove boot belt cloak robe mask",
    "material": "material pbr wood stone grass dirt metal fabric leather",
    "texture": "texture albedo normal roughness metallic mask diffuse",
}


def _ensure_unity() -> tuple[bool, str]:
    if _UNITY is None:
        return False, "UnityBridge is not initialized"
    if not _UNITY.is_connected():
        return False, "Could not connect to the Unity Editor"
    return True, ""


def _project_root() -> Path:
    project = _UNITY.call("get_project_info", {}, timeout=10)
    data_path = Path(project["data_path"])
    return data_path.parent


def _autopilot_dir() -> Path:
    path = _project_root() / "AutopilotData"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return value.strip("_")[:48] or "task"


def _safety_path() -> Path:
    return _autopilot_dir() / "safety_mode.json"


def _task_queue_path() -> Path:
    return _autopilot_dir() / "task_queue.json"


def _current_safety_mode() -> str:
    data = _read_json(_safety_path(), {"mode": "edit"})
    mode = str(data.get("mode", "edit")).lower()
    return mode if mode in _SAFETY_MODES else "edit"


def _normalize_category(category: str) -> str:
    category = (category or "").strip().lower()
    aliases = {
        "trees": "tree",
        "forest": "tree",
        "agac": "tree",
        "ağaç": "tree",
        "rocks": "rock",
        "kaya": "rock",
        "tas": "rock",
        "taş": "rock",
        "ground": "material",
        "zemin": "material",
        "props": "prop",
        "weapons": "weapon",
        "characters": "character",
    }
    return aliases.get(category, category)


@tool(description="Run a visual and structural QA pass on the active Unity scene. Captures a SceneView screenshot when possible and reports material, lighting, camera, and performance risks.")
def unity_run_visual_qa(capture_screenshot: bool = True) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "run_visual_qa",
            {"capture_screenshot": capture_screenshot},
            timeout=120,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Profile the active Unity scene for editor performance: object counts, renderers, lights, shadow casters, vertices, triangles, materials, and optimization suggestions.")
def unity_profile_scene_performance(max_objects: int = 10000) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "profile_scene_performance",
            {"max_objects": max_objects},
            timeout=120,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a safe copy of the active Unity scene before risky edits. Use before deleting, clearing, large generation, or material conversions.")
def unity_create_scene_snapshot(label: str = "manual") -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call("create_scene_snapshot", {"label": label}, timeout=60)
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Restore/open a previously created Unity scene snapshot from Assets/AutopilotSnapshots.")
def unity_restore_scene_snapshot(snapshot_path: str) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call("restore_scene_snapshot", {"path": snapshot_path}, timeout=60)
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Build a persistent semantic asset knowledge base under AutopilotData. Use this when the AI cannot find realistic project assets reliably.")
def unity_build_asset_knowledge_base(
    output_relative: str = "AutopilotData/asset_knowledge.json",
    max_per_category: int = 80,
) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        root = _project_root()
        out_path = root / output_relative
        categories: dict[str, Any] = {}
        for category, query in _CATEGORY_QUERIES.items():
            result = asset_tools.unity_search_assets_semantic(
                query=query,
                category=category,
                max_results=max_per_category,
                group_by="folder",
                instantiable_only=False,
            )
            rows = result.get("results", []) if isinstance(result, dict) else []
            categories[category] = {
                "query": query,
                "count": len(rows),
                "top_assets": rows[:max_per_category],
            }

        payload = {
            "ok": True,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project_root": str(root),
            "categories": categories,
        }
        _write_json(out_path, payload)

        md_path = out_path.with_suffix(".md")
        lines = ["# UnityTools Asset Knowledge Base", ""]
        for category, data in categories.items():
            lines.append(f"## {category} ({data['count']})")
            for asset in data["top_assets"][:20]:
                score = asset.get("score", "-")
                quality = asset.get("quality_score", asset.get("score", "-"))
                lines.append(f"- {asset.get('name')} | score={score} quality={quality} | {asset.get('path')}")
            lines.append("")
        md_path.write_text("\n".join(lines), encoding="utf-8")
        return {
            "ok": True,
            "json_path": str(out_path),
            "markdown_path": str(md_path),
            "categories": {k: v["count"] for k, v in categories.items()},
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Rank real Unity prefab/model candidates by semantic relevance and practical quality. Use before placing realistic assets.")
def unity_rank_prefab_quality(query: str, category: str = "", max_results: int = 25) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        category = _normalize_category(category)
        result = asset_tools.unity_search_assets_semantic(
            query=query,
            category=category,
            max_results=max_results * 2,
            instantiable_only=True,
        )
        assets = result.get("results", []) if isinstance(result, dict) else []
        ranked = []
        for asset in assets:
            path = str(asset.get("path", ""))
            lower = path.lower()
            quality = float(asset.get("score", 0.0))
            reasons: list[str] = []
            ext = asset.get("extension", "")
            if ext == ".prefab":
                quality += 18
                reasons.append("Prefab is easiest to instantiate safely.")
            elif ext in {".fbx", ".glb", ".gltf"}:
                quality += 8
                reasons.append("Model asset can be instantiated.")
            if any(term in lower for term in ("pbr", "polyhaven", "real", "hd", "scan")):
                quality += 12
                reasons.append("Path suggests realistic/PBR source.")
            if any(term in lower for term in ("broken", "backup", "old", "tmp", "test")):
                quality -= 16
                reasons.append("Path suggests possible low-quality or temporary asset.")
            if "sketchfab" in lower:
                quality += 4
                reasons.append("Sketchfab source; verify material import after placement.")
            if asset.get("category") == category and category:
                quality += 10
                reasons.append("Detected category matches request.")
            enriched = dict(asset)
            enriched["quality_score"] = round(quality, 3)
            enriched["quality_reasons"] = reasons or ["Ranked by semantic match and instantiability."]
            ranked.append(enriched)
        ranked.sort(key=lambda item: item.get("quality_score", 0), reverse=True)
        return {
            "ok": True,
            "query": query,
            "category": category,
            "count": len(ranked[:max_results]),
            "results": ranked[:max_results],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a deterministic scene operation plan from a natural language prompt. It chooses safe tools, snapshot points, and validation steps before editing.")
def unity_plan_scene_operation(prompt: str, safety_mode: str = "") -> dict:
    mode = (safety_mode or _current_safety_mode()).lower()
    if mode not in _SAFETY_MODES:
        mode = "edit"
    text = (prompt or "").lower()
    steps: list[dict[str, Any]] = [
        {
            "step": "snapshot",
            "tool": "unity_create_scene_snapshot",
            "why": "Large or visual edits should be reversible.",
            "params": {"label": _slug(prompt)[:32]},
        },
        {
            "step": "catalog",
            "tool": "unity_get_scene_catalog",
            "why": "Understand scene objects by name, hierarchy, materials, and components instead of tags.",
            "params": {"max_results": 5000},
        },
    ]
    if any(w in text for w in ("asset", "prefab", "realistic", "real", "relis", "tree", "rock", "prop")):
        steps.append({
            "step": "asset_knowledge",
            "tool": "unity_build_asset_knowledge_base",
            "why": "Use real project assets before falling back to primitives.",
            "params": {"max_per_category": 80},
        })
    if any(w in text for w in ("forest", "orman", "terrain", "zemin", "80", "100", "120")):
        steps.append({
            "step": "bulk_generation",
            "tool": "unity_create_optimized_forest_scene",
            "why": "Bulk generation avoids hundreds of small RPC calls and timeouts.",
            "params": {"tree_count": 100, "rock_count": 18, "terrain_size": 120.0, "clear_scene": mode != "safe"},
        })
    if any(w in text for w in ("pink", "pembe", "magenta", "material", "shader", "texture", "bozuk", "kayma")):
        steps.append({
            "step": "material_repair",
            "tool": "unity_auto_convert_materials_to_pipeline",
            "why": "Convert broken/unsupported materials while preserving textures.",
            "params": {"query": "", "category": "", "max": 5000},
        })
    if any(w in text for w in ("delete", "sil", "remove", "clear", "temizle", "kaldir", "kaldır")):
        steps.append({
            "step": "semantic_delete",
            "tool": "unity_delete_scene_objects_semantic",
            "why": "Delete by semantic name/material/component, not Unity tags.",
            "blocked_in_safe_mode": mode == "safe",
            "params": {"query": "target from prompt", "max": 500},
        })
    steps.extend([
        {
            "step": "performance",
            "tool": "unity_profile_scene_performance",
            "why": "Find heavy renderers, lights, triangles, shadows, and optimization opportunities.",
            "params": {"max_objects": 10000},
        },
        {
            "step": "visual_qa",
            "tool": "unity_run_visual_qa",
            "why": "Capture visual evidence and report material/camera/light risks.",
            "params": {"capture_screenshot": True},
        },
        {
            "step": "save",
            "tool": "unity_save_scene",
            "why": "Persist successful edits.",
            "params": {},
        },
    ])
    return {"ok": True, "safety_mode": mode, "prompt": prompt, "steps": steps}


@tool(description="Convert broken or unsupported scene materials to the active render pipeline (HDRP/URP/Built-in) while preserving texture maps. Use for pink/magenta scenes.")
def unity_auto_convert_materials_to_pipeline(query: str = "", category: str = "", max: int = 5000) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = _UNITY.call(
            "repair_material_issues",
            {
                "query": query,
                "category": category,
                "tint": False,
                "palette": "forest",
                "include_unsupported": True,
                "max": max,
            },
            timeout=240,
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set Autopilot safety mode. safe = no destructive/clear-scene edits, edit = normal Undo-aware edits, destructive = allow clears/deletes after snapshots.")
def unity_set_autopilot_safety_mode(mode: str = "edit") -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    mode = (mode or "edit").lower()
    if mode not in _SAFETY_MODES:
        return {"ok": False, "error": f"Invalid safety mode '{mode}'. Use safe, edit, or destructive."}
    data = {"mode": mode, "updated_at": datetime.now().isoformat(timespec="seconds")}
    _write_json(_safety_path(), data)
    return {"ok": True, **data, "path": str(_safety_path())}


@tool(description="Get current Autopilot safety mode and task queue summary.")
def unity_get_autopilot_safety_mode() -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    data = _read_json(_safety_path(), {"mode": "edit"})
    queue = _read_json(_task_queue_path(), {"tasks": []})
    tasks = queue.get("tasks", []) if isinstance(queue, dict) else []
    return {
        "ok": True,
        "mode": _current_safety_mode(),
        "path": str(_safety_path()),
        "task_count": len(tasks),
        "open_tasks": len([t for t in tasks if isinstance(t, dict) and t.get("status") not in {"done", "failed"}]),
    }


@tool(description="Create a persistent Autopilot task queue under AutopilotData/task_queue.json so long jobs can be tracked inside Unity chat.")
def unity_create_task_queue(title: str, tasks: list[str]) -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    normalized = [
        {
            "id": index + 1,
            "title": str(task),
            "status": "pending",
            "note": "",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        for index, task in enumerate(tasks or [])
        if str(task).strip()
    ]
    payload = {
        "ok": True,
        "title": title,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "tasks": normalized,
    }
    _write_json(_task_queue_path(), payload)
    return {"ok": True, "path": str(_task_queue_path()), "title": title, "task_count": len(normalized), "tasks": normalized}


@tool(description="Read the persistent Autopilot task queue.")
def unity_get_task_queue() -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    data = _read_json(_task_queue_path(), {"title": "", "tasks": []})
    return {"ok": True, "path": str(_task_queue_path()), **(data if isinstance(data, dict) else {"tasks": []})}


@tool(description="Update one task in the persistent Autopilot task queue. Status values: pending, running, done, failed, skipped.")
def unity_update_task_status(task_id: int, status: str, note: str = "") -> dict:
    ok, error = _ensure_unity()
    if not ok:
        return {"ok": False, "error": error}
    data = _read_json(_task_queue_path(), {"title": "", "tasks": []})
    if not isinstance(data, dict):
        data = {"title": "", "tasks": []}
    tasks = data.setdefault("tasks", [])
    valid = {"pending", "running", "done", "failed", "skipped"}
    status = (status or "").lower()
    if status not in valid:
        return {"ok": False, "error": f"Invalid status '{status}'. Use one of {sorted(valid)}."}
    for task in tasks:
        if isinstance(task, dict) and int(task.get("id", -1)) == int(task_id):
            task["status"] = status
            task["note"] = note
            task["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _write_json(_task_queue_path(), data)
            return {"ok": True, "path": str(_task_queue_path()), "task": task}
    return {"ok": False, "error": f"Task id {task_id} not found.", "path": str(_task_queue_path())}
