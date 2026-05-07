"""Unreal Editor tools exposed to the LLM."""
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..bridges.unreal import UnrealBridge
from ..core.config import Config
from ..core.tool_registry import tool

_UNREAL: UnrealBridge | None = None


def _bridge() -> UnrealBridge:
    global _UNREAL
    if _UNREAL is None:
        _UNREAL = UnrealBridge(Config.load())
    return _UNREAL


def _ensure_unreal() -> tuple[bool, str]:
    try:
        if not _bridge().connect(timeout=2.0):
            return False, "Unreal Editor bridge is not connected. Open Unreal project and enable UnrealToolsBridge plugin."
        return True, ""
    except Exception as exc:
        return False, str(exc)


@tool(description="Ping the Unreal Editor bridge.")
def unreal_ping() -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("ping", {}, timeout=5)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Get Unreal project, engine, content directory, and current map information.")
def unreal_get_project_info() -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("get_project_info", {}, timeout=10)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="List actors in the current Unreal level.")
def unreal_list_level_actors(max_results: int = 500) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("list_level_actors", {"max_results": max_results}, timeout=30)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Find Unreal level actors by semantic query/category such as tree, rock, light, camera, ground, character.")
def unreal_find_level_actors_semantic(query: str = "", category: str = "", max_results: int = 100) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("find_level_actors_semantic", {"query": query, "category": category, "max_results": max_results}, timeout=30)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Search Unreal /Game assets semantically by query/category.")
def unreal_search_assets_semantic(query: str = "", category: str = "", max_results: int = 100) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("search_assets_semantic", {"query": query, "category": category, "max_results": max_results}, timeout=60)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Get grouped summary of Unreal /Game assets by semantic category.")
def unreal_get_asset_catalog_summary(max_assets: int = 5000) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("get_asset_catalog_summary", {"max_assets": max_assets}, timeout=60)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Spawn a basic Unreal actor: cube, sphere, cylinder, plane, point_light, directional_light, camera.")
def unreal_spawn_basic_actor(type: str = "cube", label: str = "UnrealToolsActor", location: dict[str, float] | None = None) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("spawn_basic_actor", {"type": type, "label": label, "location": location or {}}, timeout=30)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Delete Unreal actors by semantic query/category. Use only after snapshot/explicit delete request.")
def unreal_delete_actors_semantic(query: str = "", category: str = "", max: int = 200) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("delete_actors_semantic", {"query": query, "category": category, "max": max}, timeout=60)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Set Unreal actor transform by name/query. location/rotation/scale are objects with x/y/z or pitch/yaw/roll.")
def unreal_set_actor_transform(query: str, location: dict[str, float] | None = None, rotation: dict[str, float] | None = None, scale: dict[str, float] | None = None) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params: dict[str, Any] = {"query": query}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale
    try:
        return {"ok": True, **_bridge().call("set_actor_transform", params, timeout=30)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Import a file into Unreal Content Browser. Supports FBX/OBJ/GLB/GLTF, textures, audio. import_mode='safe_static' avoids broken skeletal FBX stalls.")
def unreal_import_asset(filename: str, destination: str = "/Game/UnityMigrated", replace_existing: bool = True, save: bool = True, import_mode: str = "safe_static") -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("import_asset", {"filename": filename, "destination": destination, "replace_existing": replace_existing, "save": save, "import_mode": import_mode}, timeout=240)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Save dirty Unreal packages after imports or level edits.")
def unreal_save_dirty_packages() -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("save_dirty_packages", {}, timeout=120)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Copy Unity project source assets into a staging folder for Unreal migration. Does not import unless Unreal bridge is also used.")
def unreal_stage_unity_assets_for_migration(unity_project: str, staging_dir: str = "UnrealMigrationStaging", max_files: int = 5000) -> dict:
    source = Path(unity_project).expanduser().resolve() / "Assets"
    if not source.exists():
        return {"ok": False, "error": f"Unity Assets folder not found: {source}"}
    staging = Path(staging_dir).expanduser().resolve()
    exts = {".fbx", ".obj", ".glb", ".gltf", ".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".exr", ".wav", ".mp3"}
    copied = []
    reused = 0
    skipped = 0
    for path in source.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in exts:
            continue
        rel = path.relative_to(source)
        dest = staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            if dest.exists() and dest.stat().st_size == path.stat().st_size:
                reused += 1
            else:
                shutil.copy2(path, dest)
            copied.append(str(dest))
        except Exception:
            skipped += 1
        if len(copied) >= max_files:
            break
    return {"ok": True, "source": str(source), "staging": str(staging), "copied_count": len(copied), "reused": reused, "skipped": skipped, "files": copied[:100]}
