"""UnrealTools Bridge auto-start script.

Copied to: <UnrealProject>/Plugins/UnrealToolsBridge/Content/Python/init_unreal.py
Requires Unreal's PythonScriptPlugin and EditorScriptingUtilities.
Protocol: newline-delimited JSON, one request -> one response.
Default port: 8777.
"""
from __future__ import annotations

import hmac
import ipaddress
import json
import math
import os
import queue
import random
import socket
import threading
import time
import traceback
from typing import Any

import unreal

_HOST = os.environ.get("UNREALTOOLS_BRIDGE_HOST", "127.0.0.1")
_PORT = int(os.environ.get("UNREALTOOLS_BRIDGE_PORT", "8777"))


def _resolve_auth_token() -> str:
    """Paylasilan token: UNITYTOOLS_BRIDGE_TOKEN -> UNITYTOOLS_SECRET -> UNITYTOOLS_KEY."""
    for key in ("UNITYTOOLS_BRIDGE_TOKEN", "UNITYTOOLS_SECRET", "UNITYTOOLS_KEY"):
        value = os.environ.get(key)
        if value and value.strip():
            return value.strip()
    return ""


def _allow_remote() -> bool:
    return os.environ.get("UNITYTOOLS_ALLOW_REMOTE", "").strip().lower() in ("1", "true", "yes", "on")


def _is_loopback_host(host: str) -> bool:
    if not host:
        return False
    if host.strip().lower() in ("localhost", "ip6-localhost", "ip6-loopback"):
        return True
    try:
        return ipaddress.ip_address(host.strip()).is_loopback
    except ValueError:
        return False


def _path_within_any(target: str, roots: list[str]) -> bool:
    """target mutlak yolu, verilen koklerden birinin altinda mi (traversal korumasi)."""
    try:
        tgt = os.path.realpath(os.path.abspath(target))
    except Exception:
        return False
    for root in roots:
        if not root:
            continue
        try:
            base = os.path.realpath(os.path.abspath(root))
        except Exception:
            continue
        try:
            if os.path.commonpath([tgt, base]) == base:
                return True
        except ValueError:
            # Farkli surucu (Windows) -> commonpath ValueError; icermez.
            continue
    return False


_AUTH_TOKEN = _resolve_auth_token()
_REQUESTS: "queue.Queue[tuple[socket.socket, dict[str, Any]]]" = queue.Queue()
_RUNNING = False
_LISTENER: socket.socket | None = None
_THREAD: threading.Thread | None = None
_TICK_HANDLE = None


def _log(message: str) -> None:
    unreal.log(f"[UnrealTools] {message}")


def _warn(message: str) -> None:
    unreal.log_warning(f"[UnrealTools] {message}")


def _send(sock: socket.socket, payload: dict[str, Any]) -> None:
    try:
        sock.sendall((json.dumps(payload, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    except Exception:
        pass


def _accept_loop() -> None:
    global _RUNNING, _LISTENER
    while _RUNNING and _LISTENER is not None:
        try:
            client, _addr = _LISTENER.accept()
            threading.Thread(target=_client_loop, args=(client,), daemon=True, name="UnrealToolsClient").start()
        except OSError:
            break
        except Exception as exc:
            if _RUNNING:
                _warn(f"accept warning: {exc}")


def _client_loop(sock: socket.socket) -> None:
    buffer = b""
    try:
        while _RUNNING:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, _, buffer = buffer.partition(b"\n")
                if not line.strip():
                    continue
                try:
                    request = json.loads(line.decode("utf-8"))
                except Exception as exc:
                    _send(sock, {"id": "", "error": {"code": 1, "message": f"Invalid JSON: {exc}"}})
                    continue
                _REQUESTS.put((sock, request))
    except Exception:
        pass


def _tick(_delta_time: float) -> bool:
    # Process a bounded number per tick so the editor stays responsive.
    for _ in range(16):
        try:
            sock, request = _REQUESTS.get_nowait()
        except queue.Empty:
            break
        response = {"id": request.get("id", "")}
        # Guvenlik: token yapilandirilmissa her istekte sabit zamanli dogrula.
        if _AUTH_TOKEN and not hmac.compare_digest(_AUTH_TOKEN, str(request.get("token") or "")):
            response["error"] = {"code": 401, "message": "Unauthorized: gecersiz veya eksik token."}
            _send(sock, response)
            continue
        try:
            method = request.get("method", "")
            params = request.get("params") or {}
            response["result"] = _dispatch(method, params)
        except Exception as exc:
            response["error"] = {"code": 1, "message": str(exc), "traceback": traceback.format_exc()}
        _send(sock, response)
    return True


def start_bridge(host: str = _HOST, port: int = _PORT) -> bool:
    global _RUNNING, _LISTENER, _THREAD, _TICK_HANDLE
    if _RUNNING:
        return True
    # Guvenlik: loopback disi bir arayuze yalnizca acik izinle baglan.
    if not _is_loopback_host(host) and not _allow_remote():
        _warn(f"host {host} loopback degil; UNITYTOOLS_ALLOW_REMOTE olmadan 127.0.0.1'e zorlaniyor.")
        host = "127.0.0.1"
    if not _AUTH_TOKEN:
        _warn("auth token yok (UNITYTOOLS_BRIDGE_TOKEN/SECRET/KEY). Kimlik dogrulama kapali; yalnizca loopback korur.")
    last_error = None
    for candidate in range(port, port + 24):
        try:
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((host, candidate))
            listener.listen(8)
            _LISTENER = listener
            _RUNNING = True
            _THREAD = threading.Thread(target=_accept_loop, daemon=True, name="UnrealToolsAccept")
            _THREAD.start()
            if _TICK_HANDLE is None:
                _TICK_HANDLE = unreal.register_slate_post_tick_callback(_tick)
            _log(f"BridgeServer listening on {host}:{candidate}")
            return True
        except Exception as exc:
            last_error = exc
            try:
                listener.close()
            except Exception:
                pass
    _warn(f"BridgeServer could not start: {last_error}")
    return False


def stop_bridge() -> None:
    global _RUNNING, _LISTENER, _TICK_HANDLE
    _RUNNING = False
    try:
        if _LISTENER:
            _LISTENER.close()
    except Exception:
        pass
    _LISTENER = None
    if _TICK_HANDLE is not None:
        try:
            unreal.unregister_slate_post_tick_callback(_TICK_HANDLE)
        except Exception:
            pass
        _TICK_HANDLE = None
    _log("BridgeServer stopped")


def _dispatch(method: str, params: dict[str, Any]) -> Any:
    handlers = {
        "ping": _ping,
        "get_project_info": _get_project_info,
        "get_scene_workbench_status": _get_scene_workbench_status,
        "list_level_actors": _list_level_actors,
        "list_selected_actors": _list_selected_actors,
        "find_level_actors_semantic": _find_level_actors_semantic,
        "search_assets_semantic": _search_assets_semantic,
        "get_asset_catalog_summary": _get_asset_catalog_summary,
        "scan_project": _scan_project,
        "list_levels": _list_levels,
        "open_level": _open_level,
        "open_level_by_name": _open_level_by_name,
        "create_basic_level": _create_basic_level,
        "setup_studio_lighting": _setup_studio_lighting,
        "create_blockout_map": _create_blockout_map,
        "apply_actor_material_palette": _apply_actor_material_palette,
        "plan_scene_lod_decimation": _plan_scene_lod_decimation,
        "place_semantic_assets": _place_semantic_assets,
        "list_ai_placed_actors": _list_ai_placed_actors,
        "cleanup_ai_placed_actors": _cleanup_ai_placed_actors,
        "prepare_open_world_ground": _prepare_open_world_ground,
        "create_arena_survivor_prototype": _create_arena_survivor_prototype,
        "apply_arena_survivor_runtime_scaffold": _apply_arena_survivor_runtime_scaffold,
        "spawn_arena_survivor_player_pawn": _spawn_arena_survivor_player_pawn,
        "spawn_arena_survivor_placeholder_enemies": _spawn_arena_survivor_placeholder_enemies,
        "reset_arena_survivor_runtime_state": _reset_arena_survivor_runtime_state,
        "simulate_arena_survivor_wave_clear": _simulate_arena_survivor_wave_clear,
        "simulate_arena_survivor_pickup_collect": _simulate_arena_survivor_pickup_collect,
        "spawn_basic_actor": _spawn_basic_actor,
        "delete_actors_semantic": _delete_actors_semantic,
        "set_actor_transform": _set_actor_transform,
        "import_asset": _import_asset,
        "save_dirty_packages": _save_dirty_packages,
    }
    if method not in handlers:
        raise RuntimeError(f"Unknown UnrealTools method: {method}")
    return handlers[method](params)


def _ping(_params: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "pong": True, "engine": str(unreal.SystemLibrary.get_engine_version())}


def _get_project_info(_params: dict[str, Any]) -> dict[str, Any]:
    world = unreal.EditorLevelLibrary.get_editor_world()
    project_dir = unreal.Paths.project_dir()
    try:
        project_dir_abs = unreal.Paths.convert_relative_path_to_full(project_dir)
    except Exception:
        project_dir_abs = os.path.abspath(project_dir)
    return {
        "ok": True,
        "engine_version": str(unreal.SystemLibrary.get_engine_version()),
        "project_dir": project_dir,
        "project_dir_abs": project_dir_abs,
        "project_content_dir": unreal.Paths.project_content_dir(),
        "map_name": world.get_name() if world else "",
    }


def _get_scene_workbench_status(params: dict[str, Any]) -> dict[str, Any]:
    """Compact read-only snapshot for the embedded scene workbench panel."""
    max_actors = int(params.get("max_actors", 800))
    top_n = int(params.get("top_n", 8))
    project = _get_project_info({})
    actors = _all_actors()[:max_actors]
    actor_counts: dict[str, int] = {}
    actor_samples: dict[str, list[dict[str, Any]]] = {}
    for actor in actors:
        if not actor:
            continue
        row = _actor_row(actor)
        category = row["category"]
        actor_counts[category] = actor_counts.get(category, 0) + 1
        actor_samples.setdefault(category, [])
        if len(actor_samples[category]) < 5:
            actor_samples[category].append(row)

    selected = _list_selected_actors({"max_results": 30})
    ai_placed = _list_ai_placed_actors({"prefix": "UT_Placed", "max_results": 300})
    lod = _plan_scene_lod_decimation(
        {
            "max_actors": max_actors,
            "top_n": top_n,
            "target_triangle_budget": int(params.get("target_triangle_budget", 5000000)),
        }
    )

    recommendations = []
    if selected.get("count", 0) == 0:
        recommendations.append("Select one or more actors before asking for targeted edits.")
    if ai_placed.get("count", 0) > 0:
        recommendations.append("Use AI cleanup preview before deleting generated actors.")
    if lod.get("over_budget"):
        recommendations.append("Scene appears over triangle budget; inspect top mesh offenders before adding more foliage.")
    if actor_counts.get("light", 0) == 0:
        recommendations.append("Add lighting/fog before visual review.")
    if actor_counts.get("camera", 0) == 0:
        recommendations.append("Add a camera before screenshot or composition review.")
    if not recommendations:
        recommendations.append("Scene status is healthy; continue with scoped placement/material actions.")

    return {
        "ok": True,
        "read_only": True,
        "project": project,
        "actors": {
            "scanned": len(actors),
            "by_category": actor_counts,
            "samples": actor_samples,
        },
        "selected": {
            "count": selected.get("count", 0),
            "by_category": selected.get("by_category", {}),
            "actors": selected.get("actors", [])[:30],
        },
        "ai_placed": {
            "prefix": "UT_Placed",
            "count": ai_placed.get("count", 0),
            "by_category": ai_placed.get("by_category", {}),
        },
        "performance": {
            "actors_with_static_mesh": lod.get("actors_with_static_mesh", 0),
            "estimated_total_triangles": lod.get("estimated_total_triangles", 0),
            "target_triangle_budget": lod.get("target_triangle_budget", 5000000),
            "over_budget": lod.get("over_budget", False),
            "top_offenders": lod.get("top_offenders", [])[:top_n],
        },
        "recommendations": recommendations,
    }


def _actor_category(actor: unreal.Actor) -> str:
    hay = f"{actor.get_name()} {actor.get_actor_label()} {actor.get_class().get_name()}".lower()
    pairs = [
        ("tree", ("tree", "pine", "oak", "forest", "foliage", "agac", "ağaç")),
        ("rock", ("rock", "stone", "boulder", "cliff", "kaya", "tas", "taş")),
        ("light", ("light", "sun", "lamp")),
        ("camera", ("camera", "cam")),
        ("character", ("character", "player", "enemy", "npc", "hero")),
        ("ground", ("landscape", "terrain", "ground", "floor", "zemin")),
    ]
    for category, tokens in pairs:
        if any(t in hay for t in tokens):
            return category
    return "other"


def _actor_row(actor: unreal.Actor) -> dict[str, Any]:
    loc = actor.get_actor_location()
    rot = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return {
        "name": actor.get_name(),
        "label": actor.get_actor_label(),
        "class": actor.get_class().get_name(),
        "category": _actor_category(actor),
        "location": {"x": loc.x, "y": loc.y, "z": loc.z},
        "rotation": {"pitch": rot.pitch, "yaw": rot.yaw, "roll": rot.roll},
        "scale": {"x": scale.x, "y": scale.y, "z": scale.z},
    }


def _all_actors() -> list[unreal.Actor]:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        return list(subsystem.get_all_level_actors())
    except Exception:
        return list(unreal.EditorLevelLibrary.get_all_level_actors())


def _list_level_actors(params: dict[str, Any]) -> dict[str, Any]:
    max_results = int(params.get("max_results", 500))
    rows = [_actor_row(a) for a in _all_actors()[:max_results] if a]
    return {"ok": True, "count": len(rows), "actors": rows}


def _selected_actors() -> list[unreal.Actor]:
    try:
        subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        return list(subsystem.get_selected_level_actors())
    except Exception:
        try:
            return list(unreal.EditorLevelLibrary.get_selected_level_actors())
        except Exception:
            return []


def _list_selected_actors(params: dict[str, Any]) -> dict[str, Any]:
    max_results = int(params.get("max_results", 100))
    rows = [_actor_row(a) for a in _selected_actors()[:max_results] if a]
    by_category: dict[str, int] = {}
    for row in rows:
        by_category[row["category"]] = by_category.get(row["category"], 0) + 1
    return {
        "ok": True,
        "read_only": True,
        "count": len(rows),
        "by_category": by_category,
        "actors": rows,
        "notes": [] if rows else ["No actors are currently selected in the Unreal level editor."],
    }


def _matches(text: str, query: str, category: str) -> bool:
    text = text.lower()
    query = (query or "").lower().strip()
    category = (category or "").lower().strip()
    if category and category not in text:
        synonyms = {
            "tree": ["tree", "pine", "oak", "forest", "foliage", "agac", "ağaç"],
            "rock": ["rock", "stone", "boulder", "cliff", "kaya", "tas", "taş"],
            "camera": ["camera", "cam"],
            "light": ["light", "sun", "lamp"],
            "ground": ["landscape", "terrain", "ground", "zemin"],
        }.get(category, [category])
        if not any(s in text for s in synonyms):
            return False
    if query:
        if "_" in query or len(query) <= 3:
            return query in text
        tokens = [t for t in query.replace("_", " ").split() if t]
        if tokens and not any(t in text for t in tokens):
            return False
    return True


def _find_level_actors_semantic(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query", "")
    category = params.get("category", "")
    max_results = int(params.get("max_results", 100))
    rows = []
    for actor in _all_actors():
        row = _actor_row(actor)
        hay = f"{row['name']} {row['label']} {row['class']} {row['category']}"
        if _matches(hay, query, category):
            rows.append(row)
        if len(rows) >= max_results:
            break
    return {"ok": True, "query": query, "category": category, "count": len(rows), "actors": rows}


def _asset_registry():
    return unreal.AssetRegistryHelpers.get_asset_registry()


def _asset_row(asset_data: unreal.AssetData) -> dict[str, Any]:
    package_name = str(asset_data.package_name)
    name = str(asset_data.asset_name)
    try:
        object_path = str(asset_data.get_soft_object_path())
    except Exception:
        object_path = f"{package_name}.{name}"
    cls = str(asset_data.asset_class_path.asset_name) if hasattr(asset_data, "asset_class_path") else str(asset_data.asset_class)
    text = f"{package_name} {object_path} {name} {cls}".lower()
    category = "other"
    for cat, words in {
        "tree": ["tree", "pine", "oak", "forest", "foliage"],
        "rock": ["rock", "stone", "boulder", "cliff"],
        "material": ["material", "mat", "mi_", "m_"],
        "texture": ["texture", "tex", "t_"],
        "character": ["character", "hero", "enemy", "npc"],
        "sound": ["sound", "audio", "wav"],
    }.items():
        if any(w in text for w in words):
            category = cat
            break
    return {"name": name, "path": object_path, "package": package_name, "class": cls, "category": category}


def _search_assets_semantic(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query", "")
    category = params.get("category", "")
    max_results = int(params.get("max_results", 100))
    registry = _asset_registry()
    assets = registry.get_assets_by_path("/Game", recursive=True)
    rows = []
    for data in assets:
        row = _asset_row(data)
        hay = f"{row['name']} {row['path']} {row['class']} {row['category']}"
        if _matches(hay, query, category):
            rows.append(row)
        if len(rows) >= max_results:
            break
    return {"ok": True, "query": query, "category": category, "count": len(rows), "results": rows}


def _get_asset_catalog_summary(params: dict[str, Any]) -> dict[str, Any]:
    max_assets = int(params.get("max_assets", 5000))
    assets = _asset_registry().get_assets_by_path("/Game", recursive=True)[:max_assets]
    counts: dict[str, int] = {}
    samples: dict[str, list[dict[str, Any]]] = {}
    for data in assets:
        row = _asset_row(data)
        cat = row["category"]
        counts[cat] = counts.get(cat, 0) + 1
        samples.setdefault(cat, [])
        if len(samples[cat]) < 8:
            samples[cat].append(row)
    return {"ok": True, "total_scanned": len(assets), "counts": counts, "samples": samples}


def _scan_project(params: dict[str, Any]) -> dict[str, Any]:
    max_assets = int(params.get("max_assets", 8000))
    max_actors = int(params.get("max_actors", 2000))
    assets = _asset_registry().get_assets_by_path("/Game", recursive=True)[:max_assets]
    asset_counts: dict[str, int] = {}
    class_counts: dict[str, int] = {}
    sample_assets: dict[str, list[dict[str, Any]]] = {}
    for data in assets:
        row = _asset_row(data)
        asset_counts[row["category"]] = asset_counts.get(row["category"], 0) + 1
        class_counts[row["class"]] = class_counts.get(row["class"], 0) + 1
        sample_assets.setdefault(row["category"], [])
        if len(sample_assets[row["category"]]) < 6:
            sample_assets[row["category"]].append(row)

    actor_counts: dict[str, int] = {}
    actor_samples: dict[str, list[dict[str, Any]]] = {}
    actors = _all_actors()[:max_actors]
    for actor in actors:
        row = _actor_row(actor)
        actor_counts[row["category"]] = actor_counts.get(row["category"], 0) + 1
        actor_samples.setdefault(row["category"], [])
        if len(actor_samples[row["category"]]) < 6:
            actor_samples[row["category"]].append(row)

    worlds = []
    for data in assets:
        row = _asset_row(data)
        if row["class"].lower() in ("world", "level"):
            worlds.append(row)
        if len(worlds) >= 30:
            break

    return {
        "ok": True,
        "project": _get_project_info({}),
        "assets": {
            "total_scanned": len(assets),
            "by_category": asset_counts,
            "by_class": dict(sorted(class_counts.items(), key=lambda kv: kv[1], reverse=True)[:30]),
            "samples": sample_assets,
            "levels": worlds,
        },
        "actors": {
            "total_scanned": len(actors),
            "by_category": actor_counts,
            "samples": actor_samples,
        },
        "recommendations": _project_recommendations(asset_counts, actor_counts),
    }


def _level_rows(query: str = "", max_results: int = 100) -> list[dict[str, Any]]:
    query_l = str(query or "").lower().strip()
    rows: list[dict[str, Any]] = []
    for data in _asset_registry().get_assets_by_path("/Game", recursive=True):
        row = _asset_row(data)
        cls = str(row.get("class", "")).lower()
        if cls not in ("world", "level"):
            continue
        hay = f"{row.get('name', '')} {row.get('path', '')} {row.get('package', '')}".lower()
        if query_l and query_l not in hay:
            continue
        rows.append(row)

    def score(row: dict[str, Any]) -> tuple[int, str]:
        name = str(row.get("name", "")).lower()
        package = str(row.get("package", "")).lower()
        if query_l and name == query_l:
            return (0, package)
        if query_l and package.endswith("/" + query_l):
            return (1, package)
        if query_l and name.startswith(query_l):
            return (2, package)
        if query_l and query_l in name:
            return (3, package)
        return (4, package)

    rows.sort(key=score)
    return rows[: max(1, int(max_results))]


def _list_levels(params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query", ""))
    max_results = int(params.get("max_results", 100))
    active = _get_project_info({})
    notes = []
    if str(active.get("map_name", "")).lower().startswith("untitled"):
        notes.append("Active map appears unsaved/temporary; save it as a level asset before relying on reopen-by-name.")
    rows = _level_rows(query, max_results)
    return {"ok": True, "query": query, "active": active, "count": len(rows), "levels": rows, "notes": notes}


def _open_level(params: dict[str, Any]) -> dict[str, Any]:
    level_path = str(params.get("level_path", "")).strip()
    if not level_path:
        raise RuntimeError("level_path is required, e.g. /Game/UnrealTools/Maps/UT_ArenaSurvivor_V001")
    if "." in level_path:
        level_path = level_path.split(".", 1)[0]
    try:
        ok = unreal.EditorLevelLibrary.load_level(level_path)
    except Exception as exc:
        return {"ok": False, "error": f"Could not open level {level_path}: {exc}"}
    return {"ok": bool(ok), "level_path": level_path, "project": _get_project_info({})}


def _open_level_by_name(params: dict[str, Any]) -> dict[str, Any]:
    name = str(params.get("name", "")).strip()
    if not name:
        raise RuntimeError("name is required, e.g. Lvl_IntroRoom")
    if name.lower().startswith("/game/"):
        opened = _open_level({"level_path": name})
        opened["matched_level"] = {"name": os.path.basename(name), "package": opened.get("level_path", name), "path": name}
        return opened

    candidates = _level_rows(name, 50)
    name_l = name.lower()
    exact = [
        row
        for row in candidates
        if str(row.get("name", "")).lower() == name_l or str(row.get("package", "")).lower().endswith("/" + name_l)
    ]
    matched = (exact or candidates)
    if not matched:
        available = _level_rows("", 20)
        return {
            "ok": False,
            "error": f"No level matched '{name}'.",
            "query": name,
            "available_count": len(available),
            "available_levels": available,
            "project": _get_project_info({}),
        }
    row = matched[0]
    opened = _open_level({"level_path": row.get("package", "")})
    opened["matched_level"] = row
    opened["query"] = name
    return opened


def _project_recommendations(asset_counts: dict[str, int], actor_counts: dict[str, int]) -> list[str]:
    recommendations = []
    if asset_counts.get("tree", 0) or asset_counts.get("rock", 0):
        recommendations.append("Use semantic asset search before primitives for foliage/rocks.")
    else:
        recommendations.append("No obvious tree/rock assets found; use blockout primitives or import assets first.")
    if actor_counts.get("camera", 0) == 0:
        recommendations.append("Add a camera before screenshots or playtest framing.")
    if actor_counts.get("light", 0) == 0:
        recommendations.append("Add directional light, skylight, and fog for readable scene lighting.")
    recommendations.append("For new work, create a snapshot or new level before destructive edits.")
    return recommendations


def _create_basic_level(params: dict[str, Any]) -> dict[str, Any]:
    name = _safe_asset_name(str(params.get("name", "UT_Studio_Level")))
    folder = str(params.get("folder", "/Game/UnrealTools/Maps")).rstrip("/")
    level_path = f"{folder}/{name}"
    try:
        unreal.EditorLevelLibrary.new_level(level_path)
    except Exception as exc:
        return {"ok": False, "error": f"Could not create/open level {level_path}: {exc}"}
    _setup_studio_lighting({"style": params.get("style", "premium")})
    if bool(params.get("save", True)):
        unreal.EditorLevelLibrary.save_current_level()
    return {"ok": True, "level_path": level_path, "map_name": _get_project_info({}).get("map_name", "")}


def _setup_studio_lighting(params: dict[str, Any]) -> dict[str, Any]:
    style = str(params.get("style", "premium")).lower()
    created = []
    if not _find_level_actors_semantic({"query": "UT_DirectionalLight", "max_results": 1}).get("actors"):
        sun = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 420))
        sun.set_actor_label("UT_DirectionalLight")
        sun.set_actor_rotation(unreal.Rotator(-42, -35, 0), False)
        _set_actor_float_property(sun, "intensity", 4.0 if style != "night" else 1.2)
        created.append(_actor_row(sun))
    if hasattr(unreal, "SkyLight") and not _find_level_actors_semantic({"query": "UT_SkyLight", "max_results": 1}).get("actors"):
        sky = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 260))
        sky.set_actor_label("UT_SkyLight")
        _set_actor_float_property(sky, "intensity", 0.7 if style != "night" else 0.25)
        created.append(_actor_row(sky))
    if hasattr(unreal, "ExponentialHeightFog") and not _find_level_actors_semantic({"query": "UT_AtmosphericFog", "max_results": 1}).get("actors"):
        fog = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0))
        fog.set_actor_label("UT_AtmosphericFog")
        _set_actor_float_property(fog, "fog_density", 0.018 if style != "night" else 0.035)
        created.append(_actor_row(fog))
    if not _find_level_actors_semantic({"query": "UT_StudioCamera", "max_results": 1}).get("actors"):
        cam_cls = unreal.CineCameraActor if hasattr(unreal, "CineCameraActor") else unreal.CameraActor
        cam = unreal.EditorLevelLibrary.spawn_actor_from_class(cam_cls, unreal.Vector(-900, -900, 520))
        cam.set_actor_label("UT_StudioCamera")
        cam.set_actor_rotation(unreal.Rotator(-24, 45, 0), False)
        created.append(_actor_row(cam))
    return {"ok": True, "style": style, "created_count": len(created), "created": created}


def _create_blockout_map(params: dict[str, Any]) -> dict[str, Any]:
    theme = str(params.get("theme", "premium_gameplay")).lower()
    size = float(params.get("size", 1800))
    create_level = bool(params.get("create_new_level", False))
    if create_level:
        level = _create_basic_level({"name": params.get("level_name", "UT_Blockout_Map"), "save": False})
        if not level.get("ok"):
            return level
    created = []
    created.append(_spawn_static_mesh_actor("UT_GroundPlane", "plane", unreal.Vector(0, 0, 0), unreal.Vector(size / 100, size / 100, 1)))
    # Landmark rhythm: one hub, four cover blocks, two gate volumes.
    placements = [
        ("UT_PlayerStart_Blockout", "cube", unreal.Vector(-650, -650, 60), unreal.Vector(1.2, 1.2, 1.2)),
        ("UT_Objective_Hub", "cylinder", unreal.Vector(0, 0, 85), unreal.Vector(2.2, 2.2, 1.7)),
        ("UT_Cover_North", "cube", unreal.Vector(0, 520, 95), unreal.Vector(3.5, 0.45, 1.9)),
        ("UT_Cover_South", "cube", unreal.Vector(0, -520, 95), unreal.Vector(3.5, 0.45, 1.9)),
        ("UT_Cover_East", "cube", unreal.Vector(520, 0, 95), unreal.Vector(0.45, 3.5, 1.9)),
        ("UT_Cover_West", "cube", unreal.Vector(-520, 0, 95), unreal.Vector(0.45, 3.5, 1.9)),
        ("UT_Gate_A", "cube", unreal.Vector(-850, 0, 140), unreal.Vector(0.5, 2.4, 2.8)),
        ("UT_Gate_B", "cube", unreal.Vector(850, 0, 140), unreal.Vector(0.5, 2.4, 2.8)),
    ]
    for label, mesh_type, location, scale in placements:
        created.append(_spawn_static_mesh_actor(label, mesh_type, location, scale))
    lighting = _setup_studio_lighting({"style": params.get("lighting", "premium")})
    if bool(params.get("save", True)):
        unreal.EditorLevelLibrary.save_current_level()
    return {
        "ok": True,
        "theme": theme,
        "created_count": len(created),
        "created": created,
        "lighting": lighting,
        "notes": [
            "Blockout uses primitives intentionally; replace with real assets after asset scan.",
            "Names use UT_* prefixes so semantic search/delete can target this generated set safely.",
        ],
    }


def _palette_material_specs(palette: str) -> dict[str, tuple[str, tuple[float, float, float]]]:
    palette = str(palette or "forest").lower()
    if palette in ("dark", "night", "grim", "karanlik"):
        return {
            "tree": ("UT_Mat_Dark_Pine", (0.05, 0.12, 0.07)),
            "dead_tree": ("UT_Mat_Dead_Wood", (0.18, 0.15, 0.12)),
            "rock": ("UT_Mat_Cold_Rock", (0.22, 0.24, 0.26)),
            "ground": ("UT_Mat_Dark_Ground", (0.10, 0.09, 0.06)),
            "character": ("UT_Mat_Muted_Character", (0.28, 0.24, 0.20)),
            "default": ("UT_Mat_Dark_Default", (0.16, 0.17, 0.17)),
        }
    if palette in ("desert", "sand", "dry", "kurak"):
        return {
            "tree": ("UT_Mat_Dry_Olive", (0.25, 0.28, 0.12)),
            "dead_tree": ("UT_Mat_Dry_Wood", (0.28, 0.20, 0.12)),
            "rock": ("UT_Mat_Warm_Rock", (0.45, 0.36, 0.26)),
            "ground": ("UT_Mat_Sand_Ground", (0.48, 0.38, 0.22)),
            "character": ("UT_Mat_Warm_Character", (0.36, 0.25, 0.18)),
            "default": ("UT_Mat_Warm_Default", (0.35, 0.30, 0.23)),
        }
    return {
        "tree": ("UT_Mat_Forest_Pine", (0.05, 0.30, 0.10)),
        "dead_tree": ("UT_Mat_Forest_Dead_Wood", (0.20, 0.16, 0.11)),
        "rock": ("UT_Mat_Forest_Rock", (0.30, 0.32, 0.30)),
        "ground": ("UT_Mat_Forest_Ground", (0.13, 0.18, 0.08)),
        "character": ("UT_Mat_Forest_Character", (0.22, 0.24, 0.18)),
        "default": ("UT_Mat_Forest_Default", (0.18, 0.22, 0.16)),
    }


def _load_or_create_color_material(asset_name: str, rgb: tuple[float, float, float]) -> Any:
    folder = "/Game/UnrealTools/Materials"
    if not unreal.EditorAssetLibrary.does_directory_exist(folder):
        unreal.EditorAssetLibrary.make_directory(folder)
    asset_path = f"{folder}/{asset_name}"
    material = unreal.EditorAssetLibrary.load_asset(asset_path)
    if material:
        return material
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    material = tools.create_asset(asset_name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if not material:
        return None
    try:
        base = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant3Vector, -400, 0
        )
        base.constant = unreal.LinearColor(float(rgb[0]), float(rgb[1]), float(rgb[2]), 1.0)
        unreal.MaterialEditingLibrary.connect_material_property(base, "", unreal.MaterialProperty.MP_BASE_COLOR)
        rough = unreal.MaterialEditingLibrary.create_material_expression(
            material, unreal.MaterialExpressionConstant, -400, 180
        )
        rough.r = 0.85
        unreal.MaterialEditingLibrary.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
        unreal.MaterialEditingLibrary.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material)
    except Exception as exc:
        _log(f"Material color setup warning for {asset_name}: {exc}")
    return material


def _actor_palette_key(actor: unreal.Actor, category: str) -> str:
    text = f"{actor.get_name()} {actor.get_actor_label()} {actor.get_class().get_name()}".lower()
    if category == "tree" and any(term in text for term in ("dead", "dry", "old", "silhouette", "kuru", "olu")):
        return "dead_tree"
    if category in ("tree", "rock", "ground", "character"):
        return category
    return "default"


def _apply_material_to_actor(actor: unreal.Actor, material: Any) -> int:
    changed_slots = 0
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        try:
            slot_count = int(comp.get_num_materials())
        except Exception:
            slot_count = 1
        for index in range(max(1, slot_count)):
            try:
                comp.set_material(index, material)
                changed_slots += 1
            except Exception:
                continue
    return changed_slots


def _apply_actor_material_palette(params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query", ""))
    category = str(params.get("category", ""))
    palette = str(params.get("palette", "forest"))
    max_actors = int(params.get("max_actors", 200))
    specs = _palette_material_specs(palette)
    materials = {key: _load_or_create_color_material(name, rgb) for key, (name, rgb) in specs.items()}
    changed = []
    skipped = []
    for actor in _all_actors():
        row = _actor_row(actor)
        hay = f"{row['name']} {row['label']} {row['class']} {row['category']}"
        if not _matches(hay, query, category):
            continue
        key = _actor_palette_key(actor, row["category"])
        material = materials.get(key) or materials.get("default")
        if not material:
            skipped.append({**row, "reason": "material_unavailable"})
            continue
        slots = _apply_material_to_actor(actor, material)
        if slots:
            changed.append({**row, "palette_key": key, "material": str(material.get_path_name()), "slots": slots})
        else:
            skipped.append({**row, "reason": "no_static_mesh_slots"})
        if len(changed) >= max_actors:
            break
    if bool(params.get("save", False)):
        try:
            unreal.EditorLevelLibrary.save_current_level()
        except Exception:
            pass
    return {
        "ok": True,
        "palette": palette,
        "query": query,
        "category": category,
        "changed_count": len(changed),
        "skipped_count": len(skipped),
        "changed": changed[:50],
        "skipped": skipped[:20],
        "materials": {key: str(mat.get_path_name()) for key, mat in materials.items() if mat},
    }


def _static_mesh_lod_count(mesh: Any) -> int:
    try:
        return int(unreal.EditorStaticMeshLibrary.get_lod_count(mesh))
    except Exception:
        try:
            return int(mesh.get_num_lods())
        except Exception:
            return 1


def _static_mesh_vertex_count(mesh: Any, lod_index: int = 0) -> int:
    try:
        return int(unreal.EditorStaticMeshLibrary.get_number_verts(mesh, lod_index))
    except Exception:
        return 0


def _plan_scene_lod_decimation(params: dict[str, Any]) -> dict[str, Any]:
    max_actors = int(params.get("max_actors", 500))
    top_n = int(params.get("top_n", 25))
    target_budget = int(params.get("target_triangle_budget", 5000000))
    rows = []
    total_estimated = 0
    scanned = 0
    for actor in _all_actors():
        if scanned >= max_actors:
            break
        scanned += 1
        actor_total = 0
        component_rows = []
        for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
            try:
                mesh = comp.get_editor_property("static_mesh")
            except Exception:
                mesh = None
            if not mesh:
                continue
            verts = _static_mesh_vertex_count(mesh, 0)
            estimated_tris = int(verts / 3) if verts else 0
            lod_count = _static_mesh_lod_count(mesh)
            actor_total += estimated_tris
            component_rows.append(
                {
                    "mesh": str(mesh.get_path_name()),
                    "lod_count": lod_count,
                    "vertices_lod0": verts,
                    "estimated_triangles": estimated_tris,
                    "needs_lod": lod_count <= 1,
                }
            )
        if component_rows:
            row = _actor_row(actor)
            row["estimated_triangles"] = actor_total
            row["components"] = component_rows[:8]
            row["recommendation"] = "add_lods_or_replace_low_poly" if actor_total > 100000 else "ok_or_minor"
            rows.append(row)
            total_estimated += actor_total
    rows.sort(key=lambda item: item.get("estimated_triangles", 0), reverse=True)
    over_budget = total_estimated > target_budget
    recommendations = []
    if over_budget:
        recommendations.append("Scene is over the target triangle budget; replace top offenders with LOD/low-poly variants first.")
    recommendations.append("Prefer Nanite/LOD setup for static meshes that remain close to the camera.")
    recommendations.append("Use instanced foliage/HISM for repeated trees and rocks instead of many unique mesh actors.")
    recommendations.append("Keep this tool read-only; apply replacements in a separate explicit step.")
    return {
        "ok": True,
        "read_only": True,
        "scanned_actors": scanned,
        "actors_with_static_mesh": len(rows),
        "estimated_total_triangles": total_estimated,
        "target_triangle_budget": target_budget,
        "over_budget": over_budget,
        "top_offenders": rows[:top_n],
        "recommendations": recommendations,
    }


def _semantic_static_mesh_candidates(query: str, category: str, limit: int = 80) -> list[dict[str, Any]]:
    registry = _asset_registry()
    assets = registry.get_assets_by_path("/Game", recursive=True)
    candidates = []
    for data in assets:
        row = _asset_row(data)
        hay = f"{row['name']} {row['path']} {row['class']} {row['category']}"
        if not _matches(hay, query, category):
            continue
        if "staticmesh" not in row["class"].lower() and row["class"].lower() != "static mesh":
            continue
        asset = unreal.EditorAssetLibrary.load_asset(row["package"])
        if not asset:
            asset = unreal.EditorAssetLibrary.load_asset(row["path"])
        if not asset:
            continue
        try:
            if not isinstance(asset, unreal.StaticMesh):
                continue
        except Exception:
            if "staticmesh" not in str(asset.get_class().get_name()).lower():
                continue
        row["asset"] = asset
        candidates.append(row)
        if len(candidates) >= limit:
            break
    return candidates


def _fallback_mesh_for_category(category: str) -> Any:
    category = str(category or "").lower()
    mesh_path = "/Engine/BasicShapes/Cube.Cube"
    if category in ("tree", "forest"):
        mesh_path = "/Engine/BasicShapes/Cylinder.Cylinder"
    elif category == "rock":
        mesh_path = "/Engine/BasicShapes/Sphere.Sphere"
    elif category == "ground":
        mesh_path = "/Engine/BasicShapes/Plane.Plane"
    return unreal.EditorAssetLibrary.load_asset(mesh_path)


def _spawn_semantic_mesh_actor(label: str, mesh: Any, location: unreal.Vector, scale: unreal.Vector) -> Any:
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, location)
    actor.set_actor_label(label)
    comp = actor.static_mesh_component
    comp.set_static_mesh(mesh)
    actor.set_actor_scale3d(scale)
    return actor


def _semantic_scale(category: str, rng: random.Random, using_fallback: bool) -> unreal.Vector:
    category = str(category or "").lower()
    if category == "rock":
        size = rng.uniform(0.7, 1.9)
        return unreal.Vector(size * 1.25, size, rng.uniform(0.45, 1.0))
    if category in ("tree", "forest"):
        if using_fallback:
            return unreal.Vector(rng.uniform(0.45, 0.8), rng.uniform(0.45, 0.8), rng.uniform(2.5, 5.5))
        size = rng.uniform(0.85, 1.35)
        return unreal.Vector(size, size, size)
    size = rng.uniform(0.85, 1.25)
    return unreal.Vector(size, size, size)


def _ground_fallback_z(x: float, y: float, default_z: float = 0.0) -> float:
    best_z = default_z
    best_dist = None
    for actor in _ground_actors():
        try:
            loc = actor.get_actor_location()
        except Exception:
            continue
        dist = abs(float(loc.x) - x) + abs(float(loc.y) - y)
        if best_dist is None or dist < best_dist:
            best_dist = dist
            best_z = float(loc.z)
    return best_z


def _ground_aligned_location(x: float, y: float, seed_z: float, offset: float) -> tuple[unreal.Vector, dict[str, Any]]:
    """Find a usable ground point for open-world placement.

    Unreal Python trace signatures vary a little across versions, so this tries
    line tracing first and gracefully falls back to known Landscape actor Z.
    """
    start = unreal.Vector(float(x), float(y), float(seed_z) + 50000.0)
    end = unreal.Vector(float(x), float(y), float(seed_z) - 50000.0)
    trace_errors = []
    try:
        world = unreal.EditorLevelLibrary.get_editor_world()
        draw_debug = unreal.DrawDebugTrace.NONE
        trace_channels = [
            getattr(unreal.TraceTypeQuery, "TRACE_TYPE_QUERY1", None),
            getattr(unreal.TraceTypeQuery, "TRACE_TYPE_QUERY2", None),
            getattr(unreal.TraceTypeQuery, "TRACE_TYPE_QUERY3", None),
        ]
        for trace_channel in [channel for channel in trace_channels if channel is not None]:
            for trace_complex in (False, True):
                try:
                    hit = unreal.SystemLibrary.line_trace_single(
                        world,
                        start,
                        end,
                        trace_channel,
                        trace_complex,
                        [],
                        draw_debug,
                        True,
                    )
                except Exception as exc:
                    trace_errors.append(str(exc))
                    continue
                hit_ok = False
                hit_result = None
                if isinstance(hit, tuple):
                    hit_ok = bool(hit[0])
                    hit_result = hit[1] if len(hit) > 1 else None
                else:
                    hit_result = hit
                    hit_ok = bool(hit)
                if not hit_ok or hit_result is None:
                    continue
                point = getattr(hit_result, "location", None) or getattr(hit_result, "impact_point", None)
                normal = getattr(hit_result, "normal", None) or getattr(hit_result, "impact_normal", None)
                hit_actor = getattr(hit_result, "actor", None)
                if point is None:
                    continue
                hit_label = ""
                hit_class = ""
                try:
                    if hit_actor:
                        hit_label = hit_actor.get_actor_label()
                        hit_class = hit_actor.get_class().get_name()
                except Exception:
                    pass
                return (
                    unreal.Vector(float(point.x), float(point.y), float(point.z) + float(offset)),
                    {
                        "aligned_to_ground": True,
                        "alignment_method": "line_trace",
                        "ground_z": float(point.z),
                        "hit_actor": hit_label,
                        "hit_class": hit_class,
                        "trace_complex": trace_complex,
                        "normal": {
                            "x": float(getattr(normal, "x", 0.0)) if normal else 0.0,
                            "y": float(getattr(normal, "y", 0.0)) if normal else 0.0,
                            "z": float(getattr(normal, "z", 1.0)) if normal else 1.0,
                        },
                    },
                )
    except Exception as exc:
        trace_errors.append(str(exc))

    fallback_z = _ground_fallback_z(float(x), float(y), float(seed_z))
    return (
        unreal.Vector(float(x), float(y), fallback_z + float(offset)),
        {
            "aligned_to_ground": bool(fallback_z != float(seed_z)),
            "alignment_method": "ground_actor_fallback",
            "ground_z": fallback_z,
            "trace_error": "; ".join(trace_errors[-3:]) if trace_errors else "no hit",
        },
    )


def _settle_actor_bottom_to_ground(actor: Any, ground_z: float, offset: float, alignment: dict[str, Any]) -> dict[str, Any]:
    """Move actor vertically so its rendered bounds sit on the target ground.

    This handles both base-pivot meshes and center-pivot meshes without needing
    per-asset metadata.
    """
    try:
        bounds = actor.get_actor_bounds(False)
        origin = bounds[0]
        extent = bounds[1]
        current = actor.get_actor_location()
        bottom_z = float(origin.z) - float(extent.z)
        target_bottom_z = float(ground_z) + float(offset)
        delta_z = target_bottom_z - bottom_z
        if abs(delta_z) > 0.01:
            actor.set_actor_location(
                unreal.Vector(float(current.x), float(current.y), float(current.z) + delta_z),
                False,
                False,
            )
        alignment = dict(alignment)
        alignment["bottom_settled"] = True
        alignment["bottom_z_before"] = bottom_z
        alignment["target_bottom_z"] = target_bottom_z
        alignment["bottom_delta_z"] = delta_z
        return alignment
    except Exception as exc:
        alignment = dict(alignment)
        alignment["bottom_settled"] = False
        alignment["bottom_settle_error"] = str(exc)
        return alignment


def _place_semantic_assets(params: dict[str, Any]) -> dict[str, Any]:
    query = str(params.get("query", ""))
    category = str(params.get("category", "tree")).lower().strip() or "tree"
    count = max(1, min(300, int(params.get("count", 12))))
    radius = max(100.0, min(10000.0, float(params.get("radius", 1200))))
    prefix = _safe_asset_name(str(params.get("prefix", "UT_Placed")))
    palette = str(params.get("palette", "")).lower().strip()
    align_to_ground = bool(params.get("align_to_ground", True))
    ground_offset = float(params.get("ground_offset", 8.0))
    center_data = params.get("center") or {}
    center = unreal.Vector(float(center_data.get("x", 0)), float(center_data.get("y", 0)), float(center_data.get("z", 0)))
    rng = random.Random(str(params.get("seed", f"{category}:{query}:{count}:{radius}")))

    plan: list[tuple[str, int]] = []
    if category in ("forest", "orman"):
        tree_count = max(1, int(count * 0.78))
        rock_count = max(1, count - tree_count)
        plan = [("tree", tree_count), ("rock", rock_count)]
    else:
        plan = [(category, count)]

    placed = []
    asset_samples = []
    fallback_count = 0
    global_index = 1
    for item_category, item_count in plan:
        candidates = _semantic_static_mesh_candidates(query or item_category, item_category, limit=80)
        if candidates:
            asset_samples.extend([{k: v for k, v in row.items() if k != "asset"} for row in candidates[:5]])
        fallback_mesh = _fallback_mesh_for_category(item_category)
        for _ in range(item_count):
            use_fallback = not candidates
            if candidates:
                chosen = candidates[global_index % len(candidates)]
                mesh = chosen.get("asset")
                source_path = chosen.get("path")
            else:
                mesh = fallback_mesh
                source_path = "fallback_basic_shape"
            if not mesh:
                continue
            angle = rng.random() * math.tau
            dist = radius * math.sqrt(rng.random())
            x = center.x + math.cos(angle) * dist
            y = center.y + math.sin(angle) * dist
            item_offset = ground_offset
            if item_category == "rock":
                item_offset = max(ground_offset, 12.0)
            if align_to_ground:
                loc, alignment = _ground_aligned_location(x, y, center.z, item_offset)
            else:
                loc = unreal.Vector(x, y, center.z)
                alignment = {"aligned_to_ground": False, "alignment_method": "disabled", "ground_z": center.z}
            label_category = "Tree" if item_category in ("tree", "forest") else item_category.title()
            label = f"{prefix}_{label_category}_{global_index:03d}"
            actor = _spawn_semantic_mesh_actor(label, mesh, loc, _semantic_scale(item_category, rng, use_fallback))
            actor.set_actor_rotation(unreal.Rotator(0, rng.uniform(0, 360), 0), False)
            alignment = _settle_actor_bottom_to_ground(actor, float(alignment.get("ground_z", loc.z)), item_offset, alignment)
            if palette:
                specs = _palette_material_specs(palette)
                key = _actor_palette_key(actor, item_category)
                spec = specs.get(key) or specs.get(item_category) or specs.get("default")
                if spec:
                    mat = _load_or_create_color_material(spec[0], spec[1])
                    if mat:
                        _apply_material_to_actor(actor, mat)
            if use_fallback:
                fallback_count += 1
            row = _actor_row(actor)
            row["source_asset"] = source_path
            row["fallback"] = use_fallback
            row["alignment"] = alignment
            placed.append(row)
            global_index += 1

    if bool(params.get("save", False)):
        try:
            unreal.EditorLevelLibrary.save_current_level()
        except Exception:
            pass

    return {
        "ok": True,
        "query": query,
        "category": category,
        "requested_count": count,
        "placed_count": len(placed),
        "fallback_count": fallback_count,
        "aligned_count": len([row for row in placed if row.get("alignment", {}).get("aligned_to_ground")]),
        "bottom_settled_count": len([row for row in placed if row.get("alignment", {}).get("bottom_settled")]),
        "used_real_assets": fallback_count < len(placed),
        "asset_samples": asset_samples[:12],
        "placed": placed[:80],
        "notes": [
            "Actors are prefixed and safe to find/delete semantically later.",
            "If fallback_count is high, import or migrate tree/rock StaticMesh assets first.",
        ],
    }


def _ai_placed_rows(prefix: str, category: str = "", max_results: int = 5000) -> list[dict[str, Any]]:
    safe_prefix = str(prefix or "UT_Placed").strip() or "UT_Placed"
    category = str(category or "").strip()
    rows = []
    for actor in _all_actors():
        if not actor:
            continue
        row = _actor_row(actor)
        if not row["label"].startswith(safe_prefix):
            continue
        hay = f"{row['name']} {row['label']} {row['class']} {row['category']}"
        if category and not _matches(hay, "", category):
            continue
        rows.append(row)
        if len(rows) >= max_results:
            break
    return rows


def _write_ai_snapshot(prefix: str, rows: list[dict[str, Any]], action: str) -> str:
    project_dir = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
    folder = os.path.join(project_dir, "Saved", "UnityToolsSnapshots")
    os.makedirs(folder, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(folder, f"{_safe_asset_name(prefix)}_{action}_{timestamp}.json")
    payload = {
        "prefix": prefix,
        "action": action,
        "created_at": timestamp,
        "map": _get_project_info({}).get("map_name", ""),
        "count": len(rows),
        "actors": rows,
    }
    with open(filename, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, default=str)
    return filename


def _list_ai_placed_actors(params: dict[str, Any]) -> dict[str, Any]:
    prefix = str(params.get("prefix", "UT_Placed")).strip() or "UT_Placed"
    max_results = int(params.get("max_results", 500))
    rows = _ai_placed_rows(prefix, max_results=max_results)
    by_category: dict[str, int] = {}
    for row in rows:
        by_category[row["category"]] = by_category.get(row["category"], 0) + 1
    return {
        "ok": True,
        "read_only": True,
        "prefix": prefix,
        "count": len(rows),
        "by_category": by_category,
        "actors": rows,
    }


def _cleanup_ai_placed_actors(params: dict[str, Any]) -> dict[str, Any]:
    prefix = str(params.get("prefix", "UT_Placed")).strip() or "UT_Placed"
    category = str(params.get("category", "")).strip()
    dry_run = bool(params.get("dry_run", False))
    rows = _ai_placed_rows(prefix, category=category, max_results=5000)
    snapshot = _write_ai_snapshot(prefix, rows, "dry_run" if dry_run else "cleanup")
    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "prefix": prefix,
            "category": category,
            "matched_count": len(rows),
            "deleted_count": 0,
            "snapshot": snapshot,
            "actors": rows[:100],
        }

    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    deleted = []
    failed = []
    labels = {row["label"] for row in rows}
    for actor in _all_actors():
        if not actor or actor.get_actor_label() not in labels:
            continue
        row = _actor_row(actor)
        try:
            ok = bool(subsystem.destroy_actor(actor))
        except Exception:
            try:
                ok = bool(unreal.EditorLevelLibrary.destroy_actor(actor))
            except Exception:
                ok = False
        if ok:
            deleted.append(row)
        else:
            failed.append(row)
    if bool(params.get("save", False)):
        try:
            unreal.EditorLevelLibrary.save_current_level()
        except Exception:
            pass
    return {
        "ok": True,
        "dry_run": False,
        "prefix": prefix,
        "category": category,
        "matched_count": len(rows),
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "snapshot": snapshot,
        "deleted": deleted[:100],
        "failed": failed[:50],
        "notes": ["Only actors whose label starts with the safe prefix were eligible for deletion."],
    }


def _ground_actors() -> list[Any]:
    rows = []
    for actor in _all_actors():
        if not actor:
            continue
        cls = actor.get_class().get_name().lower()
        label = actor.get_actor_label().lower()
        if "landscape" in cls or "terrain" in cls or "landscape" in label or "ground" in label:
            rows.append(actor)
    return rows


def _try_apply_ground_material(actor: Any, material: Any) -> bool:
    applied = False
    for prop in ("landscape_material", "LandscapeMaterial", "override_material", "OverrideMaterial"):
        try:
            actor.set_editor_property(prop, material)
            applied = True
        except Exception:
            pass
    for comp in actor.get_components_by_class(unreal.PrimitiveComponent):
        try:
            comp.set_material(0, material)
            applied = True
        except Exception:
            continue
    return applied


def _prepare_open_world_ground(params: dict[str, Any]) -> dict[str, Any]:
    style = str(params.get("style", "forest")).lower().strip() or "forest"
    size = max(1000.0, min(200000.0, float(params.get("size", 12000))))
    scatter_count = max(0, min(80, int(params.get("scatter_count", 0))))
    specs = _palette_material_specs(style)
    ground_spec = specs.get("ground") or specs.get("default")
    material = _load_or_create_color_material(ground_spec[0], ground_spec[1]) if ground_spec else None

    ground = _ground_actors()
    material_applied = []
    created_ground = None
    if ground and material:
        for actor in ground:
            if _try_apply_ground_material(actor, material):
                material_applied.append(_actor_row(actor))
    if not ground:
        mesh = unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Plane.Plane")
        actor = _spawn_semantic_mesh_actor(
            "UT_OpenWorld_GroundPlane",
            mesh,
            unreal.Vector(0, 0, 0),
            unreal.Vector(size / 100.0, size / 100.0, 1.0),
        )
        if material:
            _apply_material_to_actor(actor, material)
        created_ground = _actor_row(actor)

    lighting = _setup_studio_lighting({"style": "premium" if style != "dark" else "night"})
    scatter = None
    if scatter_count > 0:
        scatter = _place_semantic_assets(
            {
                "query": "",
                "category": "forest",
                "count": scatter_count,
                "radius": min(size * 0.35, 6000.0),
                "prefix": "UT_Placed",
                "palette": style,
                "align_to_ground": True,
                "ground_offset": 8.0,
                "save": False,
                "seed": f"ground:{style}:{scatter_count}:{_get_project_info({}).get('map_name', '')}",
            }
        )

    if bool(params.get("save", False)):
        try:
            unreal.EditorLevelLibrary.save_current_level()
        except Exception:
            pass

    return {
        "ok": True,
        "style": style,
        "existing_ground_count": len(ground),
        "material_applied_count": len(material_applied),
        "created_ground": created_ground,
        "material": str(material.get_path_name()) if material else "",
        "lighting": lighting,
        "scatter": scatter,
        "notes": [
            "Existing Landscape actors are preferred; fallback plane is only created when no ground exists.",
            "Scatter uses UT_Placed prefix so it can be safely cleaned later.",
        ],
    }


def _create_arena_survivor_prototype(params: dict[str, Any]) -> dict[str, Any]:
    """Create a first playable-slice arena layout for the evolving studio loop."""
    level_name = str(params.get("level_name", "UT_ArenaSurvivor_V001"))
    create_level = bool(params.get("create_new_level", True))
    enemy_count = max(4, min(32, int(params.get("enemy_count", 12))))
    pickup_count = max(2, min(16, int(params.get("pickup_count", 6))))
    arena_size = float(params.get("arena_size", 2200))

    if create_level:
        level = _create_basic_level({"name": level_name, "save": False, "style": "premium"})
        if not level.get("ok"):
            return level

    created: list[dict[str, Any]] = []
    created.append(_spawn_static_mesh_actor("ASV001_Ground_Arena", "plane", unreal.Vector(0, 0, 0), unreal.Vector(arena_size / 100, arena_size / 100, 1)))
    created.append(_spawn_static_mesh_actor("ASV001_Player_Start", "cube", unreal.Vector(-720, -720, 70), unreal.Vector(1.1, 1.1, 1.4)))
    created.append(_spawn_static_mesh_actor("ASV001_Objective_Core", "cylinder", unreal.Vector(0, 0, 120), unreal.Vector(2.0, 2.0, 2.4)))

    cover_layout = [
        ("ASV001_Cover_North_01", unreal.Vector(-360, 560, 95), unreal.Vector(2.8, 0.5, 1.9)),
        ("ASV001_Cover_North_02", unreal.Vector(420, 560, 95), unreal.Vector(2.2, 0.5, 1.7)),
        ("ASV001_Cover_South_01", unreal.Vector(-420, -560, 95), unreal.Vector(2.2, 0.5, 1.7)),
        ("ASV001_Cover_South_02", unreal.Vector(360, -560, 95), unreal.Vector(2.8, 0.5, 1.9)),
        ("ASV001_Cover_East_01", unreal.Vector(620, -220, 95), unreal.Vector(0.5, 2.3, 1.8)),
        ("ASV001_Cover_West_01", unreal.Vector(-620, 220, 95), unreal.Vector(0.5, 2.3, 1.8)),
    ]
    for label, location, scale in cover_layout:
        created.append(_spawn_static_mesh_actor(label, "cube", location, scale))

    import math

    enemy_rows = []
    radius = arena_size * 0.36
    for idx in range(enemy_count):
        angle = (math.tau * idx) / enemy_count
        wave = 1 + (idx % 3)
        loc = unreal.Vector(math.cos(angle) * radius, math.sin(angle) * radius, 70)
        label = f"ASV001_EnemySpawn_W{wave}_{idx + 1:02d}"
        row = _spawn_static_mesh_actor(label, "cylinder", loc, unreal.Vector(0.65, 0.65, 1.4))
        row["wave"] = wave
        enemy_rows.append(row)
        created.append(row)

    pickup_rows = []
    pickup_radius = arena_size * 0.22
    for idx in range(pickup_count):
        angle = (math.tau * idx) / pickup_count + 0.35
        loc = unreal.Vector(math.cos(angle) * pickup_radius, math.sin(angle) * pickup_radius, 65)
        label = f"ASV001_Pickup_HealthOrAmmo_{idx + 1:02d}"
        row = _spawn_static_mesh_actor(label, "sphere", loc, unreal.Vector(0.55, 0.55, 0.55))
        pickup_rows.append(row)
        created.append(row)

    gate_rows = []
    for idx, (x, y) in enumerate([(-1030, 0), (1030, 0), (0, -1030), (0, 1030)], 1):
        row = _spawn_static_mesh_actor(f"ASV001_WaveGate_{idx:02d}", "cube", unreal.Vector(x, y, 150), unreal.Vector(0.5 if x else 2.8, 2.8 if x else 0.5, 3.0))
        gate_rows.append(row)
        created.append(row)

    created.append(_spawn_static_mesh_actor("ASV001_MetricMarker_FunClarity", "sphere", unreal.Vector(0, -220, 170), unreal.Vector(0.35, 0.35, 0.35)))
    lighting = _setup_studio_lighting({"style": "premium"})

    if bool(params.get("save", True)):
        unreal.EditorLevelLibrary.save_current_level()

    return {
        "ok": True,
        "prototype": "arena_survivor",
        "version": "v001",
        "level_name": level_name,
        "created_count": len(created),
        "enemy_spawn_count": len(enemy_rows),
        "pickup_count": len(pickup_rows),
        "gate_count": len(gate_rows),
        "created": created,
        "lighting": lighting,
        "hypothesis": "Short readable waves around a central objective create a clearer first survival loop than a large unfocused arena.",
        "metrics_to_collect": [
            "fun_score",
            "clarity_score",
            "time_to_understand_objective_seconds",
            "first_death_time_seconds",
            "fps_average",
        ],
        "next_steps": [
            "Replace primitive enemy spawns with character or pawn blueprints.",
            "Add HUD objective prompt and health/stamina bars.",
            "Add wave manager and pickup interaction.",
            "Record playtest metrics into GameStudioData/experiments.jsonl.",
        ],
    }


def _apply_arena_survivor_runtime_scaffold(params: dict[str, Any]) -> dict[str, Any]:
    """Replace pure markers with UnrealToolsRuntime gameplay scaffold actors."""
    prefix = str(params.get("prefix", "ASV001"))
    save = bool(params.get("save", True))
    wave_cls = _load_runtime_class("ASVWaveManager")
    spawn_cls = _load_runtime_class("ASVEnemySpawnPoint")
    pickup_cls = _load_runtime_class("ASVPickup")
    if not wave_cls or not spawn_cls or not pickup_cls:
        return {
            "ok": False,
            "error": "UnrealToolsRuntime classes are not loaded. Rebuild/restart Unreal after installing the plugin.",
            "missing": {
                "ASVWaveManager": not bool(wave_cls),
                "ASVEnemySpawnPoint": not bool(spawn_cls),
                "ASVPickup": not bool(pickup_cls),
            },
        }

    actors = _all_actors()
    labels = {a.get_actor_label(): a for a in actors if a}
    created = []

    if f"{prefix}_RuntimeWaveManager" not in labels:
        objective = labels.get(f"{prefix}_Objective_Core")
        location = objective.get_actor_location() if objective else unreal.Vector(0, 0, 160)
        manager = unreal.EditorLevelLibrary.spawn_actor_from_class(wave_cls, location)
        manager.set_actor_label(f"{prefix}_RuntimeWaveManager")
        _set_editor_property_any(manager, ["total_waves", "TotalWaves"], 3)
        _set_editor_property_any(manager, ["current_wave", "CurrentWave"], 1)
        _set_editor_property_any(manager, ["enemies_per_wave", "EnemiesPerWave"], 4)
        _set_editor_property_any(manager, ["objective", "Objective"], "Survive 3 waves near the core")
        _call_if_exists(manager, "update_objective_text")
        created.append(_actor_row(manager))

    spawn_markers = sorted(
        [a for a in actors if a and a.get_actor_label().startswith(f"{prefix}_EnemySpawn_")],
        key=lambda a: a.get_actor_label(),
    )
    for idx, marker in enumerate(spawn_markers, 1):
        label = f"{prefix}_RuntimeEnemySpawn_{idx:02d}"
        if label in labels:
            continue
        loc = marker.get_actor_location()
        spawned = unreal.EditorLevelLibrary.spawn_actor_from_class(spawn_cls, loc)
        spawned.set_actor_label(label)
        wave = _parse_wave_index(marker.get_actor_label())
        _set_editor_property_any(spawned, ["wave_index", "WaveIndex"], wave)
        _set_editor_property_any(spawned, ["spawn_delay", "SpawnDelay"], float(idx % 4) * 0.35)
        created.append(_actor_row(spawned))

    pickup_markers = sorted(
        [a for a in actors if a and a.get_actor_label().startswith(f"{prefix}_Pickup_")],
        key=lambda a: a.get_actor_label(),
    )
    for idx, marker in enumerate(pickup_markers, 1):
        label = f"{prefix}_RuntimePickup_{idx:02d}"
        if label in labels:
            continue
        loc = marker.get_actor_location()
        pickup = unreal.EditorLevelLibrary.spawn_actor_from_class(pickup_cls, loc)
        pickup.set_actor_label(label)
        _set_editor_property_any(pickup, ["pickup_type", "PickupType"], "Health" if idx % 2 else "Ammo")
        _set_editor_property_any(pickup, ["amount", "Amount"], 25.0 if idx % 2 else 30.0)
        created.append(_actor_row(pickup))

    if save:
        unreal.EditorLevelLibrary.save_current_level()

    return {
        "ok": True,
        "prefix": prefix,
        "created_count": len(created),
        "created": created,
        "runtime_classes": ["ASVWaveManager", "ASVEnemySpawnPoint", "ASVPickup"],
        "notes": [
            "Runtime scaffold keeps the project Blueprint-first while adding reusable C++ plugin actors.",
            "Generated runtime actors use the ASV001_Runtime* prefix for safe future mutation.",
        ],
    }


def _spawn_arena_survivor_placeholder_enemies(params: dict[str, Any]) -> dict[str, Any]:
    prefix = str(params.get("prefix", "ASV001"))
    wave_index = int(params.get("wave_index", 1))
    max_enemies = max(1, min(64, int(params.get("max_enemies", 4))))
    save = bool(params.get("save", True))
    enemy_cls = _load_runtime_class("ASVPlaceholderEnemy")
    if not enemy_cls:
        return {"ok": False, "error": "ASVPlaceholderEnemy class is not loaded. Rebuild/restart Unreal after installing the plugin."}

    actors = _all_actors()
    objective = next((a for a in actors if a and a.get_actor_label() == f"{prefix}_RuntimeWaveManager"), None)
    if objective is None:
        objective = next((a for a in actors if a and a.get_actor_label() == f"{prefix}_Objective_Core"), None)

    spawn_points = [
        a for a in actors
        if a
        and a.get_actor_label().startswith(f"{prefix}_RuntimeEnemySpawn_")
        and _get_editor_property_any(a, ["wave_index", "WaveIndex"], 1) == wave_index
    ]
    if not spawn_points:
        spawn_points = [
            a for a in actors
            if a
            and a.get_actor_label().startswith(f"{prefix}_EnemySpawn_")
            and _parse_wave_index(a.get_actor_label()) == wave_index
        ]

    created = []
    existing = []
    existing_labels = {a.get_actor_label() for a in actors if a}
    for idx, point in enumerate(spawn_points[:max_enemies], 1):
        label = f"{prefix}_PlaceholderEnemy_W{wave_index}_{idx:02d}"
        if label in existing_labels:
            existing_actor = next((a for a in actors if a and a.get_actor_label() == label), None)
            if existing_actor:
                _set_editor_property_any(existing_actor, ["target_actor", "TargetActor"], objective)
                existing.append(_actor_row(existing_actor))
            continue
        loc = point.get_actor_location()
        enemy = unreal.EditorLevelLibrary.spawn_actor_from_class(enemy_cls, loc)
        enemy.set_actor_label(label)
        _set_editor_property_any(enemy, ["target_actor", "TargetActor"], objective)
        _set_editor_property_any(enemy, ["move_speed", "MoveSpeed"], 120.0 + 15.0 * (wave_index - 1))
        created.append(_actor_row(enemy))

    manager = next((a for a in actors if a and a.get_actor_label() == f"{prefix}_RuntimeWaveManager"), None)
    if manager is not None:
        _set_editor_property_any(manager, ["current_wave", "CurrentWave"], wave_index)
        _set_editor_property_any(manager, ["alive_enemies", "AliveEnemies"], len(created) + len(existing))
        _call_if_exists(manager, "update_objective_text")

    if save:
        unreal.EditorLevelLibrary.save_current_level()

    return {
        "ok": True,
        "prefix": prefix,
        "wave_index": wave_index,
        "created_count": len(created),
        "existing_count": len(existing),
        "created": created,
        "existing": existing,
        "target": _actor_row(objective) if objective else None,
        "notes": [
            "Placeholder enemies are visible editor actors and runtime-capable.",
            "At play time ASVWaveManager can also spawn enemies from ASVEnemySpawnPoint actors.",
        ],
    }


def _spawn_arena_survivor_player_pawn(params: dict[str, Any]) -> dict[str, Any]:
    prefix = str(params.get("prefix", "ASV001"))
    save = bool(params.get("save", True))
    pawn_cls = _load_runtime_class("ASVPlayerCombatPawn")
    if not pawn_cls:
        return {"ok": False, "error": "ASVPlayerCombatPawn class is not loaded. Rebuild/restart Unreal after installing the plugin."}

    actors = _all_actors()
    label = f"{prefix}_RuntimePlayerCombatPawn"
    existing = next((a for a in actors if a and a.get_actor_label() == label), None)
    marker = next((a for a in actors if a and a.get_actor_label() == f"{prefix}_Player_Start"), None)
    loc = marker.get_actor_location() if marker else unreal.Vector(-720, -720, 110)
    loc.z = max(loc.z, 120)

    if existing:
        existing.set_actor_location(loc, False, False)
        pawn = existing
        created = False
    else:
        pawn = unreal.EditorLevelLibrary.spawn_actor_from_class(pawn_cls, loc)
        pawn.set_actor_label(label)
        created = True

    try:
        pawn.set_actor_rotation(unreal.Rotator(0, 45, 0), False)
    except Exception:
        pass

    if save:
        unreal.EditorLevelLibrary.save_current_level()
    return {
        "ok": True,
        "prefix": prefix,
        "created": created,
        "pawn": _actor_row(pawn),
        "controls": {
            "move": "WASD",
            "look": "Mouse",
            "fire": "Left mouse button",
        },
        "notes": ["The pawn is AutoPossessPlayer0 and can damage ASVPlaceholderEnemy via ApplyArenaDamage."],
    }


def _reset_arena_survivor_runtime_state(params: dict[str, Any]) -> dict[str, Any]:
    prefix = str(params.get("prefix", "ASV001"))
    save = bool(params.get("save", True))
    actors = _all_actors()
    destroyed = []
    reset_pickups = []

    for actor in actors:
        if not actor:
            continue
        label = actor.get_actor_label()
        cls = actor.get_class().get_name().lower()
        if label.startswith(f"{prefix}_PlaceholderEnemy_") or label.startswith(f"{prefix}_RuntimeEnemy_") or "asvplaceholderenemy" in cls:
            destroyed.append(label)
            try:
                unreal.EditorLevelLibrary.destroy_actor(actor)
            except Exception:
                pass

    for actor in _all_actors():
        if not actor:
            continue
        label = actor.get_actor_label()
        if label.startswith(f"{prefix}_RuntimePickup_"):
            _set_editor_property_any(actor, ["b_collected", "bCollected"], False)
            actor.set_actor_hidden_in_game(False)
            actor.set_actor_enable_collision(True)
            reset_pickups.append(label)

    manager = next((a for a in _all_actors() if a and a.get_actor_label() == f"{prefix}_RuntimeWaveManager"), None)
    if manager:
        if not _call_method_any(manager, ["reset_runtime_state", "ResetRuntimeState"]):
            _set_editor_property_any(manager, ["current_wave", "CurrentWave"], 1)
            _set_editor_property_any(manager, ["alive_enemies", "AliveEnemies"], 0)
            _set_editor_property_any(manager, ["collected_pickups", "CollectedPickups"], 0)
            _set_editor_property_any(manager, ["b_victory", "bVictory"], False)
            _call_if_exists(manager, "update_objective_text")

    if save:
        unreal.EditorLevelLibrary.save_current_level()
    return {
        "ok": True,
        "prefix": prefix,
        "destroyed_enemies": destroyed,
        "reset_pickups": reset_pickups,
        "manager_status": _manager_status(manager),
        "notes": ["Runtime state reset keeps layout actors intact and removes only transient enemies."],
    }


def _simulate_arena_survivor_wave_clear(params: dict[str, Any]) -> dict[str, Any]:
    """Defeat visible placeholder enemies so the wave state can be tested from chat."""
    prefix = str(params.get("prefix", "ASV001"))
    wave_index = int(params.get("wave_index", 0))
    count = int(params.get("count", 0))
    save = bool(params.get("save", True))

    actors = _all_actors()
    manager = next((a for a in actors if a and a.get_actor_label() == f"{prefix}_RuntimeWaveManager"), None)
    enemies = []
    for actor in actors:
        if not actor:
            continue
        label = actor.get_actor_label()
        cls = actor.get_class().get_name().lower()
        if not (label.startswith(f"{prefix}_PlaceholderEnemy_") or label.startswith(f"{prefix}_RuntimeEnemy_") or "asvplaceholderenemy" in cls):
            continue
        if wave_index > 0 and f"_W{wave_index}_" not in label:
            continue
        enemies.append(actor)

    if count > 0:
        enemies = enemies[:count]

    defeated = []
    for enemy in enemies:
        label = enemy.get_actor_label()
        called = _call_method_any(enemy, ["apply_arena_damage", "ApplyArenaDamage"], 99999.0, manager)
        if not called:
            called = _call_method_any(enemy, ["defeat", "Defeat"])
        if not called:
            if manager:
                _call_method_any(manager, ["register_enemy_defeated", "RegisterEnemyDefeated"])
            try:
                unreal.EditorLevelLibrary.destroy_actor(enemy)
                called = True
            except Exception:
                called = False
        defeated.append({"label": label, "ok": called})

    status = _manager_status(manager)
    if save:
        unreal.EditorLevelLibrary.save_current_level()
    return {
        "ok": True,
        "prefix": prefix,
        "wave_index": wave_index,
        "defeated_count": len([row for row in defeated if row["ok"]]),
        "defeated": defeated,
        "manager_status": status,
        "notes": ["Use this after spawning placeholder enemies to verify wave transitions without waiting for combat input."],
    }


def _simulate_arena_survivor_pickup_collect(params: dict[str, Any]) -> dict[str, Any]:
    """Collect runtime pickups from chat so objective/HUD binding can be verified."""
    prefix = str(params.get("prefix", "ASV001"))
    count = int(params.get("count", 1))
    save = bool(params.get("save", True))

    actors = _all_actors()
    manager = next((a for a in actors if a and a.get_actor_label() == f"{prefix}_RuntimeWaveManager"), None)
    pickups = [
        a for a in actors
        if a and a.get_actor_label().startswith(f"{prefix}_RuntimePickup_")
        and not bool(_get_editor_property_any(a, ["b_collected", "bCollected"], False))
    ]
    if count > 0:
        pickups = pickups[:count]

    collected = []
    for pickup in pickups:
        label = pickup.get_actor_label()
        called = _call_method_any(pickup, ["collect", "Collect"], manager)
        if not called:
            _set_editor_property_any(pickup, ["b_collected", "bCollected"], True)
            pickup.set_actor_hidden_in_game(True)
            pickup.set_actor_enable_collision(False)
            if manager:
                pickup_type = _get_editor_property_any(pickup, ["pickup_type", "PickupType"], "Health")
                amount = float(_get_editor_property_any(pickup, ["amount", "Amount"], 25.0))
                _call_method_any(manager, ["register_pickup_collected", "RegisterPickupCollected"], pickup_type, amount)
            called = True
        collected.append({"label": label, "ok": called})

    status = _manager_status(manager)
    if save:
        unreal.EditorLevelLibrary.save_current_level()
    return {
        "ok": True,
        "prefix": prefix,
        "collected_count": len([row for row in collected if row["ok"]]),
        "collected": collected,
        "manager_status": status,
        "notes": ["Pickup collection updates ASVWaveManager so objective prompt/HUD logic has a single source of truth."],
    }


def _load_runtime_class(name: str):
    cls = getattr(unreal, name, None)
    if cls:
        return cls
    try:
        return unreal.load_class(None, f"/Script/UnrealToolsRuntime.{name}")
    except Exception:
        return None


def _set_editor_property_any(obj: Any, names: list[str], value: Any) -> bool:
    for name in names:
        try:
            obj.set_editor_property(name, value)
            return True
        except Exception:
            continue
    return False


def _get_editor_property_any(obj: Any, names: list[str], fallback: Any = None) -> Any:
    for name in names:
        try:
            return obj.get_editor_property(name)
        except Exception:
            continue
    return fallback


def _call_if_exists(obj: Any, name: str) -> bool:
    fn = getattr(obj, name, None)
    if not callable(fn):
        return False
    try:
        fn()
        return True
    except Exception:
        return False


def _call_method_any(obj: Any, names: list[str], *args: Any) -> bool:
    if obj is None:
        return False
    for name in names:
        fn = getattr(obj, name, None)
        if not callable(fn):
            continue
        try:
            fn(*args)
            return True
        except Exception:
            continue
    return False


def _manager_status(manager: Any) -> dict[str, Any] | None:
    if manager is None:
        return None
    text = ""
    for name in ("get_status_text", "GetStatusText"):
        fn = getattr(manager, name, None)
        if callable(fn):
            try:
                text = str(fn())
                break
            except Exception:
                pass
    return {
        "label": manager.get_actor_label(),
        "current_wave": _get_editor_property_any(manager, ["current_wave", "CurrentWave"], 0),
        "total_waves": _get_editor_property_any(manager, ["total_waves", "TotalWaves"], 0),
        "alive_enemies": _get_editor_property_any(manager, ["alive_enemies", "AliveEnemies"], 0),
        "collected_pickups": _get_editor_property_any(manager, ["collected_pickups", "CollectedPickups"], 0),
        "victory": _get_editor_property_any(manager, ["b_victory", "bVictory"], False),
        "text": text,
    }


def _parse_wave_index(label: str) -> int:
    import re

    match = re.search(r"_W(\d+)_", label)
    if not match:
        return 1
    try:
        return int(match.group(1))
    except Exception:
        return 1


def _spawn_static_mesh_actor(label: str, mesh_type: str, location: unreal.Vector, scale: unreal.Vector) -> dict[str, Any]:
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(unreal.StaticMeshActor, location)
    actor.set_actor_label(label)
    mesh_path = "/Engine/BasicShapes/Cube.Cube"
    if mesh_type == "sphere":
        mesh_path = "/Engine/BasicShapes/Sphere.Sphere"
    elif mesh_type == "cylinder":
        mesh_path = "/Engine/BasicShapes/Cylinder.Cylinder"
    elif mesh_type == "plane":
        mesh_path = "/Engine/BasicShapes/Plane.Plane"
    mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
    actor.static_mesh_component.set_static_mesh(mesh)
    actor.set_actor_scale3d(scale)
    return _actor_row(actor)


def _set_actor_float_property(actor: unreal.Actor, name: str, value: float) -> None:
    try:
        actor.set_editor_property(name, value)
        return
    except Exception:
        pass
    for component in actor.get_components_by_class(unreal.ActorComponent):
        try:
            if component.has_editor_property(name):
                component.set_editor_property(name, value)
                return
        except Exception:
            continue


def _safe_asset_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value.strip())
    cleaned = cleaned.strip("_")
    return cleaned or "UT_Studio_Level"


def _spawn_basic_actor(params: dict[str, Any]) -> dict[str, Any]:
    actor_type = str(params.get("type", "cube")).lower()
    label = str(params.get("label", params.get("name", f"UnrealTools_{actor_type}")))
    loc_data = params.get("location") or {}
    location = unreal.Vector(float(loc_data.get("x", 0)), float(loc_data.get("y", 0)), float(loc_data.get("z", 0)))
    cls = unreal.StaticMeshActor
    if actor_type in ("point_light", "pointlight", "light"):
        cls = unreal.PointLight
    elif actor_type in ("directional_light", "directional"):
        cls = unreal.DirectionalLight
    elif actor_type in ("camera", "cine_camera"):
        cls = unreal.CineCameraActor if hasattr(unreal, "CineCameraActor") else unreal.CameraActor
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(cls, location)
    actor.set_actor_label(label)
    if cls == unreal.StaticMeshActor:
        mesh_path = "/Engine/BasicShapes/Cube.Cube"
        if actor_type in ("sphere",):
            mesh_path = "/Engine/BasicShapes/Sphere.Sphere"
        elif actor_type in ("cylinder",):
            mesh_path = "/Engine/BasicShapes/Cylinder.Cylinder"
        elif actor_type in ("plane",):
            mesh_path = "/Engine/BasicShapes/Plane.Plane"
        mesh = unreal.EditorAssetLibrary.load_asset(mesh_path)
        comp = actor.static_mesh_component
        comp.set_static_mesh(mesh)
    return {"ok": True, "actor": _actor_row(actor)}


def _delete_actors_semantic(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query", "")
    category = params.get("category", "")
    max_count = int(params.get("max", 200))
    deleted = []
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    for actor in _all_actors():
        row = _actor_row(actor)
        hay = f"{row['name']} {row['label']} {row['class']} {row['category']}"
        if _matches(hay, query, category):
            deleted.append(row)
            subsystem.destroy_actor(actor)
        if len(deleted) >= max_count:
            break
    return {"ok": True, "deleted_count": len(deleted), "deleted": deleted}


def _set_actor_transform(params: dict[str, Any]) -> dict[str, Any]:
    query = params.get("query", params.get("name", ""))
    found = _find_level_actors_semantic({"query": query, "max_results": 1}).get("actors", [])
    if not found:
        return {"ok": False, "error": f"Actor not found: {query}"}
    label = found[0]["label"]
    actor = next((a for a in _all_actors() if a.get_actor_label() == label or a.get_name() == found[0]["name"]), None)
    if actor is None:
        return {"ok": False, "error": f"Actor not found after lookup: {query}"}
    if "location" in params:
        loc = params["location"] or {}
        actor.set_actor_location(unreal.Vector(float(loc.get("x", 0)), float(loc.get("y", 0)), float(loc.get("z", 0))), False, False)
    if "rotation" in params:
        rot = params["rotation"] or {}
        actor.set_actor_rotation(unreal.Rotator(float(rot.get("pitch", 0)), float(rot.get("yaw", 0)), float(rot.get("roll", 0))), False)
    if "scale" in params:
        sc = params["scale"] or {}
        actor.set_actor_scale3d(unreal.Vector(float(sc.get("x", 1)), float(sc.get("y", 1)), float(sc.get("z", 1))))
    return {"ok": True, "actor": _actor_row(actor)}


def _import_asset(params: dict[str, Any]) -> dict[str, Any]:
    filename = os.path.abspath(str(params.get("filename", params.get("path", ""))))
    destination = str(params.get("destination", "/Game/UnityMigrated"))
    import_mode = str(params.get("import_mode", "safe_static")).lower()
    if not filename or not os.path.exists(filename):
        return {"ok": False, "error": f"File not found: {filename}"}
    # Guvenlik: kaynak yolu izinli koklerle sinirla (proje + opsiyonel import root);
    # rastgele mutlak yol / traversal ile makineden dosya cekmeyi engelle.
    allowed_roots: list[str] = []
    try:
        proj = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
        if proj:
            allowed_roots.append(proj)
    except Exception:
        pass
    import_root = os.environ.get("UNREALTOOLS_IMPORT_ROOT", "").strip()
    if import_root:
        allowed_roots.append(import_root)
    if not _path_within_any(filename, allowed_roots):
        return {
            "ok": False,
            "error": (
                "Import source izinli kok disinda. Proje klasoru altina koy ya da "
                f"UNREALTOOLS_IMPORT_ROOT ayarla: {filename}"
            ),
        }
    # Hedef icerik yolu yalnizca /Game altinda olabilir.
    if not destination.startswith("/Game"):
        return {"ok": False, "error": f"destination must be under /Game: {destination}"}
    task = unreal.AssetImportTask()
    task.filename = filename
    task.destination_path = destination
    task.automated = True
    task.save = bool(params.get("save", True))
    task.replace_existing = bool(params.get("replace_existing", True))
    if import_mode == "safe_static" and filename.lower().endswith(".fbx") and hasattr(unreal, "FbxImportUI"):
        options = unreal.FbxImportUI()
        options.automated_import_should_detect_type = False
        options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
        options.import_mesh = True
        options.import_as_skeletal = False
        options.import_animations = False
        task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    return {"ok": True, "filename": filename, "destination": destination, "imported_object_paths": list(task.imported_object_paths)}


def _save_dirty_packages(_params: dict[str, Any]) -> dict[str, Any]:
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return {"ok": True}


start_bridge()
