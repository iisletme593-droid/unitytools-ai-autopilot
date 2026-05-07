"""UnrealTools Bridge auto-start script.

Copied to: <UnrealProject>/Plugins/UnrealToolsBridge/Content/Python/init_unreal.py
Requires Unreal's PythonScriptPlugin and EditorScriptingUtilities.
Protocol: newline-delimited JSON, one request -> one response.
Default port: 8777.
"""
from __future__ import annotations

import json
import os
import queue
import socket
import threading
import time
import traceback
from typing import Any

import unreal

_HOST = os.environ.get("UNREALTOOLS_BRIDGE_HOST", "127.0.0.1")
_PORT = int(os.environ.get("UNREALTOOLS_BRIDGE_PORT", "8777"))
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
        "list_level_actors": _list_level_actors,
        "find_level_actors_semantic": _find_level_actors_semantic,
        "search_assets_semantic": _search_assets_semantic,
        "get_asset_catalog_summary": _get_asset_catalog_summary,
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
    return {
        "ok": True,
        "engine_version": str(unreal.SystemLibrary.get_engine_version()),
        "project_dir": unreal.Paths.project_dir(),
        "project_content_dir": unreal.Paths.project_content_dir(),
        "map_name": world.get_name() if world else "",
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
    object_path = str(asset_data.get_soft_object_path())
    name = str(asset_data.asset_name)
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
