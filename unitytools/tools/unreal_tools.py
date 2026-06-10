"""Unreal Editor tools exposed to the LLM."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
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


def _memory_dir() -> Path:
    return Path.cwd() / "GameStudioData"


def _remember_active_level(result: dict[str, Any]) -> None:
    """Persist selected level intent without making editor calls depend on it."""
    if not isinstance(result, dict) or not result.get("ok"):
        return
    project = result.get("project") if isinstance(result.get("project"), dict) else {}
    matched_level = result.get("matched_level") if isinstance(result.get("matched_level"), dict) else {}
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "unreal",
        "project_dir_abs": project.get("project_dir_abs") or project.get("project_dir") or "",
        "map_name": project.get("map_name") or result.get("map_name") or "",
        "level_path": result.get("level_path") or matched_level.get("package") or "",
        "matched_level": matched_level,
    }
    try:
        target_dir = _memory_dir()
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "active_unreal_level.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _read_active_level_memory() -> dict[str, Any]:
    try:
        path = _memory_dir() / "active_unreal_level.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


@tool(description="Get a compact read-only Unreal scene workbench status: active map, selected actors, actor categories, AI-placed counts, and performance risk.")
def unreal_get_scene_workbench_status(max_actors: int = 800, top_n: int = 8, target_triangle_budget: int = 5_000_000) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "max_actors": max_actors,
        "top_n": top_n,
        "target_triangle_budget": target_triangle_budget,
    }
    try:
        result = {"ok": True, **_bridge().call("get_scene_workbench_status", params, timeout=120)}
        memory = _read_active_level_memory()
        if memory:
            active_map = str(result.get("project", {}).get("map_name", ""))
            remembered_map = str(memory.get("map_name", ""))
            result["game_studio_memory"] = memory
            result["target_scene_mismatch"] = bool(remembered_map and active_map and remembered_map != active_map)
            if result["target_scene_mismatch"]:
                recommendations = list(result.get("recommendations", []))
                recommendations.insert(
                    0,
                    f"Remembered target scene is {remembered_map}, but active editor map is {active_map}. Open/confirm the target scene before write actions.",
                )
                result["recommendations"] = recommendations
        return result
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


@tool(description="List currently selected Unreal level actors with semantic categories. Read-only.")
def unreal_list_selected_actors(max_results: int = 100) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("list_selected_actors", {"max_results": max_results}, timeout=30)}
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


@tool(description="Studio scan for Unreal project: project info, current level actors, /Game asset categories/classes, levels, and recommendations.")
def unreal_scan_project(max_assets: int = 8000, max_actors: int = 2000) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("scan_project", {"max_assets": max_assets, "max_actors": max_actors}, timeout=90)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="List available Unreal levels/maps under /Game with active map info.")
def unreal_list_levels(query: str = "", max_results: int = 100) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("list_levels", {"query": query, "max_results": max_results}, timeout=60)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Remember the currently active Unreal level/map as the GameStudio target scene without changing the level.")
def unreal_remember_active_level() -> dict:
    info = unreal_get_project_info()
    if not info.get("ok"):
        return info
    map_name = str(info.get("map_name", ""))
    levels = unreal_list_levels(query=map_name, max_results=10) if map_name else {"ok": False, "levels": []}
    matched = {}
    if levels.get("ok"):
        for row in levels.get("levels", []):
            if str(row.get("name", "")).lower() == map_name.lower():
                matched = row
                break
        if not matched and levels.get("levels"):
            matched = levels["levels"][0]
    result = {
        "ok": True,
        "project": info,
        "map_name": map_name,
        "level_path": matched.get("package", ""),
        "matched_level": matched,
        "notes": [] if matched else ["Active map was remembered by name, but no saved World asset matched it yet."],
    }
    _remember_active_level(result)
    return result


@tool(description="Open an existing Unreal level/map by package path, e.g. /Game/UnrealTools/Maps/UT_ArenaSurvivor_V001.")
def unreal_open_level(level_path: str) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = {"ok": True, **_bridge().call("open_level", {"level_path": level_path}, timeout=120)}
        _remember_active_level(result)
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Open an existing Unreal level/map by display name, e.g. Lvl_IntroRoom or UT_ArenaSurvivor_V001.")
def unreal_open_level_by_name(name: str, remember: bool = True) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        result = {"ok": True, **_bridge().call("open_level_by_name", {"name": name, "remember": remember}, timeout=120)}
        if remember:
            _remember_active_level(result)
        return result
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Create/open a new Unreal level under /Game/UnrealTools/Maps and add basic lighting/camera.")
def unreal_create_basic_level(name: str = "UT_Studio_Level", folder: str = "/Game/UnrealTools/Maps", style: str = "premium", save: bool = True) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("create_basic_level", {"name": name, "folder": folder, "style": style, "save": save}, timeout=120)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Set up Unreal studio lighting: directional light, sky light, fog, and camera if missing.")
def unreal_setup_studio_lighting(style: str = "premium") -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("setup_studio_lighting", {"style": style}, timeout=60)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Create a safe primitive Unreal blockout map with named gameplay landmarks, cover, gates, lighting, and camera.")
def unreal_create_blockout_map(theme: str = "premium_gameplay", size: float = 1800, create_new_level: bool = False, level_name: str = "UT_Blockout_Map", lighting: str = "premium", save: bool = True) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "theme": theme,
        "size": size,
        "create_new_level": create_new_level,
        "level_name": level_name,
        "lighting": lighting,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("create_blockout_map", params, timeout=180)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Apply a simple safe material color palette to matching Unreal level actors by semantic query/category such as tree, rock, ground, character, or all.")
def unreal_apply_actor_material_palette(query: str = "", category: str = "", palette: str = "forest", max_actors: int = 200, save: bool = False) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "query": query,
        "category": category,
        "palette": palette,
        "max_actors": max_actors,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("apply_actor_material_palette", params, timeout=120)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Analyze current Unreal level static meshes and return a LOD/decimation plan for heavy actors without modifying the scene.")
def unreal_plan_scene_lod_decimation(max_actors: int = 500, top_n: int = 25, target_triangle_budget: int = 5_000_000) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "max_actors": max_actors,
        "top_n": top_n,
        "target_triangle_budget": target_triangle_budget,
    }
    try:
        return {"ok": True, **_bridge().call("plan_scene_lod_decimation", params, timeout=120)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Place matching Unreal assets semantically into the current level, e.g. trees, rocks, forest scatter. Uses /Game StaticMesh assets first and safe primitive fallback if none are found.")
def unreal_place_semantic_assets(
    query: str = "",
    category: str = "tree",
    count: int = 12,
    radius: float = 1200,
    prefix: str = "UT_Placed",
    palette: str = "",
    align_to_ground: bool = True,
    ground_offset: float = 8.0,
    save: bool = False,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "query": query,
        "category": category,
        "count": count,
        "radius": radius,
        "prefix": prefix,
        "palette": palette,
        "align_to_ground": align_to_ground,
        "ground_offset": ground_offset,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("place_semantic_assets", params, timeout=180)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="List AI-placed Unreal actors by safe prefix, usually UT_Placed. Read-only.")
def unreal_list_ai_placed_actors(prefix: str = "UT_Placed", max_results: int = 500) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("list_ai_placed_actors", {"prefix": prefix, "max_results": max_results}, timeout=30)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Safely cleanup AI-placed Unreal actors by prefix, usually UT_Placed. It snapshots matching actors before deletion and will not touch unrelated scene objects.")
def unreal_cleanup_ai_placed_actors(prefix: str = "UT_Placed", category: str = "", dry_run: bool = False, save: bool = False) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "prefix": prefix,
        "category": category,
        "dry_run": dry_run,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("cleanup_ai_placed_actors", params, timeout=90)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Prepare an open-world ground/terrain setup: apply simple ground material to existing Landscape or create a large fallback plane, then add lighting/fog and optional semantic tree/rock scatter.")
def unreal_prepare_open_world_ground(style: str = "forest", size: float = 12000, scatter_count: int = 0, save: bool = False) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "style": style,
        "size": size,
        "scatter_count": scatter_count,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("prepare_open_world_ground", params, timeout=240)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Create the first Self-Evolving GameStudio Arena Survivor prototype in Unreal: arena, objective core, cover, enemy spawn markers, pickups, gates, lighting, and metrics.")
def unreal_create_arena_survivor_prototype(
    level_name: str = "UT_ArenaSurvivor_V001",
    create_new_level: bool = True,
    enemy_count: int = 12,
    pickup_count: int = 6,
    arena_size: float = 2200,
    save: bool = True,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "level_name": level_name,
        "create_new_level": create_new_level,
        "enemy_count": enemy_count,
        "pickup_count": pickup_count,
        "arena_size": arena_size,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("create_arena_survivor_prototype", params, timeout=180)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Apply UnrealToolsRuntime actors to an Arena Survivor prototype: runtime wave manager, enemy spawn point actors, and pickup actors from ASV marker layout.")
def unreal_apply_arena_survivor_runtime_scaffold(
    prefix: str = "ASV001",
    save: bool = True,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("apply_arena_survivor_runtime_scaffold", {"prefix": prefix, "save": save}, timeout=180)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Spawn or reposition the Arena Survivor runtime player combat pawn in the current Unreal level. WASD moves, mouse looks, left click damages placeholder enemies.")
def unreal_spawn_arena_survivor_player_pawn(
    prefix: str = "ASV001",
    save: bool = True,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("spawn_arena_survivor_player_pawn", {"prefix": prefix, "save": save}, timeout=120)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Spawn visible runtime placeholder enemies from Arena Survivor spawn points for a wave, targeting the objective/wave manager.")
def unreal_spawn_arena_survivor_placeholder_enemies(
    prefix: str = "ASV001",
    wave_index: int = 1,
    max_enemies: int = 4,
    save: bool = True,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "prefix": prefix,
        "wave_index": wave_index,
        "max_enemies": max_enemies,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("spawn_arena_survivor_placeholder_enemies", params, timeout=180)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Reset Arena Survivor runtime state in the current Unreal level: remove transient enemies, reset pickups, and reset wave manager counters.")
def unreal_reset_arena_survivor_runtime_state(
    prefix: str = "ASV001",
    save: bool = True,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    try:
        return {"ok": True, **_bridge().call("reset_arena_survivor_runtime_state", {"prefix": prefix, "save": save}, timeout=120)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Defeat Arena Survivor placeholder enemies in the current Unreal level to test wave state transitions without manual combat.")
def unreal_simulate_arena_survivor_wave_clear(
    prefix: str = "ASV001",
    wave_index: int = 0,
    count: int = 0,
    save: bool = True,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "prefix": prefix,
        "wave_index": wave_index,
        "count": count,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("simulate_arena_survivor_wave_clear", params, timeout=120)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@tool(description="Collect Arena Survivor runtime pickups in the current Unreal level to test pickup overlap/objective prompt binding.")
def unreal_simulate_arena_survivor_pickup_collect(
    prefix: str = "ASV001",
    count: int = 1,
    save: bool = True,
) -> dict:
    ok, error = _ensure_unreal()
    if not ok:
        return {"ok": False, "error": error}
    params = {
        "prefix": prefix,
        "count": count,
        "save": save,
    }
    try:
        return {"ok": True, **_bridge().call("simulate_arena_survivor_pickup_collect", params, timeout=120)}
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
