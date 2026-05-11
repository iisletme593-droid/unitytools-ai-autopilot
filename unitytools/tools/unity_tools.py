"""Unity-related tools exposed to the LLM."""
from __future__ import annotations


from ..core.tool_registry import tool


_UNITY = None  # type: ignore


@tool(description="Test the Unity Editor bridge connection.")
def unity_ping() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    connected = _UNITY.is_connected()
    if not connected:
        return {"ok": False, "error": "Could not connect to the Unity Editor"}
    return {"ok": _UNITY.ping(), "connected": True}


@tool(description="List GameObjects in the active Unity scene. Use max_count to avoid huge responses.")
def unity_list_scene_objects(max_count: int = 200) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_scene_objects", {"max_count": max_count})
        if not isinstance(result, dict):
            return {"ok": True, "objects": result}
        objects = result.get("objects", [])
        return {
            "ok": True,
            "scene": result.get("scene"),
            "count": result.get("count", len(objects)),
            "truncated": bool(result.get("truncated", len(objects) > max_count)),
            "objects": objects,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find active-scene GameObjects by partial name match. Prefer this when checking whether an object exists.")
def unity_find_scene_objects(name_contains: str, max_count: int = 50) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "find_scene_objects",
            {"name_contains": name_contains, "max_count": max_count},
        )
        matches = result.get("objects", []) if isinstance(result, dict) else []
        return {
            "ok": True,
            "query": name_contains,
            "count": result.get("count", len(matches)) if isinstance(result, dict) else len(matches),
            "truncated": bool(result.get("truncated", False)) if isinstance(result, dict) else False,
            "objects": matches,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a Unity primitive. type can be Cube, Sphere, Cylinder, Capsule, Plane, or Quad.")
def unity_create_primitive(
    type: str,
    name: str = "",
    position_x: float = 0.0,
    position_y: float = 0.0,
    position_z: float = 0.0,

) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "create_primitive",
            {
                "type": type,
                "name": name or type,
                "position": {"x": position_x, "y": position_y, "z": position_z},
            },
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Copy an asset into the Unity project's Assets folder and refresh AssetDatabase.")
def unity_import_asset(src_path: str, dst_relative: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "import_asset",
            {"src_path": src_path, "dst_relative": dst_relative},
        )
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Save the active Unity scene.")
def unity_save_scene() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        _UNITY.call("save_scene")
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List Unity scene assets in the project. Defaults to editable Assets/ scenes only; set include_packages=true to include package sample scenes.")
def unity_list_scenes(max_results: int = 200, include_packages: bool = False) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "list_scenes",
            {"max_results": max_results, "include_packages": include_packages},
            timeout=30,
        )
        if isinstance(result, dict) and not include_packages:
            scenes = result.get("scenes", [])
            if isinstance(scenes, list):
                filtered = [
                    scene for scene in scenes
                    if isinstance(scene, dict) and str(scene.get("path", "")).startswith("Assets/")
                ]
                result = dict(result)
                result["scenes"] = filtered
                result["returned"] = len(filtered)
        return {"ok": True, **(result if isinstance(result, dict) else {"scenes": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Open/switch to a Unity scene by asset path, for example Assets/Scenes/Main.unity. Save or snapshot before opening if the current scene has important changes.")
def unity_open_scene(path: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("open_scene", {"path": path}, timeout=60)
        return {"ok": bool(result.get("ok", True)) if isinstance(result, dict) else True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject position by object name.")
def unity_set_position(name: str, x: float, y: float, z: float) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "set_transform",
            {"name": name, "position": {"x": x, "y": y, "z": z}},
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject rotation in Euler angles by object name.")
def unity_set_rotation(name: str, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "set_transform",
            {"name": name, "rotation": {"x": x, "y": y, "z": z}},
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject local scale by object name.")
def unity_set_scale(name: str, x: float = 1.0, y: float = 1.0, z: float = 1.0) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "set_transform",
            {"name": name, "scale": {"x": x, "y": y, "z": z}},
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject material color. RGB values 0-1.")
def unity_set_material_color(name: str, r: float = 1.0, g: float = 1.0, b: float = 1.0, a: float = 1.0) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "set_material_color",
            {"name": name, "r": r, "g": g, "b": b, "a": a},
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Execute a Unity Editor menu item by path. Example: 'Window/General/Scene'.")
def unity_execute_menu_item(path: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("execute_menu_item", {"path": path})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Get Unity project and editor info.")
def unity_get_project_info() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("get_project_info")
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Delete a GameObject by name from the active scene.")
def unity_delete_object(name: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("delete_object", {"name": name})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Duplicate a GameObject by name.")
def unity_duplicate_object(name: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("duplicate_object", {"name": name})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create an empty GameObject.")
def unity_create_empty(name: str = "Empty", position_x: float = 0.0, position_y: float = 0.0, position_z: float = 0.0) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "create_empty",
            {
                "name": name,
                "position": {"x": position_x, "y": position_y, "z": position_z},
            },
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject's parent by name. Use empty string for parent to unparent.")
def unity_set_parent(child: str, parent: str = "") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("set_parent", {"child": child, "parent": parent})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject active or inactive.")
def unity_set_active(name: str, active: bool = True) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("set_active", {"name": name, "active": active})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject's tag.")
def unity_set_tag(name: str, tag: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("set_tag", {"name": name, "tag": tag})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a GameObject's layer index.")
def unity_set_layer(name: str, layer: int = 0) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("set_layer", {"name": name, "layer": layer})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Add a component to a GameObject by type name. Examples: Rigidbody, Light, Camera, BoxCollider, SphereCollider, CapsuleCollider, MeshCollider, MeshRenderer, AudioSource.")
def unity_add_component(name: str, type: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("add_component", {"name": name, "type": type})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Remove a component from a GameObject by type name.")
def unity_remove_component(name: str, type: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("remove_component", {"name": name, "type": type})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Get component list of a GameObject.")
def unity_get_component_info(name: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("get_component_info", {"name": name})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Get detailed info about a GameObject: position, rotation, scale, active, tag, layer, parent, child count, components.")
def unity_get_object_details(name: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("get_object_details", {"name": name})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a light in the scene. light_type can be Point, Directional, Spot, Area. RGB 0-1.")
def unity_create_light(
    name: str = "Light",
    light_type: str = "Point",
    position_x: float = 0.0,
    position_y: float = 0.0,
    position_z: float = 0.0,
    r: float = 1.0,
    g: float = 1.0,
    b: float = 1.0,
    intensity: float = 1.0,
    range_val: float = 10.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "create_light",
            {
                "name": name,
                "light_type": light_type,
                "position": {"x": position_x, "y": position_y, "z": position_z},
                "color": {"r": r, "g": g, "b": b, "a": 1.0},
                "intensity": intensity,
                "range": range_val,
            },
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Adjust an existing Light component by name. Pass only the fields you want to change; missing fields keep their current Unity values. RGB 0-1; intensity >=0; spot_angle 1-179; shadows_enabled toggles soft shadows.")
def unity_set_light_properties(
    name: str,
    r: float = -1.0,
    g: float = -1.0,
    b: float = -1.0,
    intensity: float = -1.0,
    range_val: float = -1.0,
    spot_angle: float = -1.0,
    shadows_enabled: int = -1,  # -1 = no change, 0 = off, 1 = on
    shadow_strength: float = -1.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not name:
        return {"ok": False, "error": "name is required"}
    params: dict = {"name": name}
    if r >= 0.0 or g >= 0.0 or b >= 0.0:
        params["color"] = {
            "r": max(0.0, r if r >= 0.0 else 0.0),
            "g": max(0.0, g if g >= 0.0 else 0.0),
            "b": max(0.0, b if b >= 0.0 else 0.0),
            "a": 1.0,
        }
    if intensity >= 0.0:
        params["intensity"] = intensity
    if range_val >= 0.0:
        params["range"] = range_val
    if spot_angle >= 0.0:
        params["spot_angle"] = spot_angle
    if shadows_enabled in (0, 1):
        params["shadows_enabled"] = bool(shadows_enabled)
    if shadow_strength >= 0.0:
        params["shadow_strength"] = shadow_strength
    try:
        result = _UNITY.call("set_light_properties", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set the scene's ambient lighting (RenderSettings). RGB 0-1, intensity >=0. mode is one of Flat / Trilight / Skybox. Affects every object that isn't lit by a direct Light component.")
def unity_set_ambient_light(
    r: float = -1.0,
    g: float = -1.0,
    b: float = -1.0,
    intensity: float = -1.0,
    mode: str = "",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    params: dict = {}
    if r >= 0.0 or g >= 0.0 or b >= 0.0:
        params["color"] = {
            "r": max(0.0, r if r >= 0.0 else 0.0),
            "g": max(0.0, g if g >= 0.0 else 0.0),
            "b": max(0.0, b if b >= 0.0 else 0.0),
            "a": 1.0,
        }
    if intensity >= 0.0:
        params["intensity"] = intensity
    if mode:
        params["mode"] = mode
    try:
        result = _UNITY.call("set_ambient_light", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List every Light in the active scene with type, intensity, color, range, shadow flag. Also returns ambient color/intensity/mode. Use this before mutating lights so you know what's there.")
def unity_list_lights() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_lights", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set a camera's world position and/or Euler rotation. Empty name targets Camera.main. Pass only the axes you want to change; the others keep their current value. Use this when you know exact transform coords; for 'frame this object' use unity_frame_object instead.")
def unity_set_camera_transform(
    name: str = "",
    position_x: float = float("nan"),
    position_y: float = float("nan"),
    position_z: float = float("nan"),
    rotation_x: float = float("nan"),
    rotation_y: float = float("nan"),
    rotation_z: float = float("nan"),
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    import math
    params: dict = {"name": name}
    pos = {}
    if not math.isnan(position_x): pos["x"] = position_x
    if not math.isnan(position_y): pos["y"] = position_y
    if not math.isnan(position_z): pos["z"] = position_z
    if pos: params["position"] = pos
    rot = {}
    if not math.isnan(rotation_x): rot["x"] = rotation_x
    if not math.isnan(rotation_y): rot["y"] = rotation_y
    if not math.isnan(rotation_z): rot["z"] = rotation_z
    if rot: params["rotation_euler"] = rot
    try:
        result = _UNITY.call("set_camera_transform", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Position a camera so it frames a named GameObject. The camera is placed on a sphere of `distance` units around the target and aimed at the target's render-bounds center. Use yaw_degrees (around Y, default -30) and pitch_degrees (tilt down, default 20) to pick the angle. camera_name='' targets Camera.main. Distance defaults to 3x the target's bounds radius — leave at 0 for auto.")
def unity_frame_object(
    target_name: str,
    camera_name: str = "",
    distance: float = 0.0,
    yaw_degrees: float = -30.0,
    pitch_degrees: float = 20.0,
    height_offset: float = 0.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not target_name:
        return {"ok": False, "error": "target_name is required"}
    params: dict = {
        "target_name": target_name,
        "camera_name": camera_name,
        "yaw_degrees": yaw_degrees,
        "pitch_degrees": pitch_degrees,
        "height_offset": height_offset,
    }
    if distance > 0:
        params["distance"] = distance
    try:
        result = _UNITY.call("frame_object", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List every Camera in the active scene with FOV, transform, ortho settings, and which one is the main camera. Read-only.")
def unity_list_cameras() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_cameras", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Add (or reconfigure) a ParticleSystem on a named GameObject using one of four presets: 'dust', 'fire', 'smoke', 'magic'. Each preset sets emission rate, lifetime, speed, color, and size to a tuned baseline you can fine-tune later with unity_set_particle_properties.")
def unity_add_particle_system(target_name: str, preset: str = "dust") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not target_name:
        return {"ok": False, "error": "target_name is required"}
    preset = (preset or "dust").lower()
    if preset not in ("dust", "fire", "smoke", "magic"):
        return {"ok": False, "error": f"unknown preset {preset!r}; use dust / fire / smoke / magic"}
    try:
        result = _UNITY.call("add_particle_system", {"target_name": target_name, "preset": preset})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Tune properties on an existing ParticleSystem by GameObject name. Pass only the fields you want to change. emission_rate >=0, start_lifetime >0, max_particles 1..10000. RGB 0-1. The object must already have a ParticleSystem component (use unity_add_particle_system first).")
def unity_set_particle_properties(
    name: str,
    emission_rate: float = -1.0,
    start_lifetime: float = -1.0,
    start_speed: float = float("nan"),
    start_size: float = -1.0,
    max_particles: int = -1,
    loop: int = -1,  # -1 = no change, 0 = off, 1 = on
    r: float = -1.0,
    g: float = -1.0,
    b: float = -1.0,
    a: float = -1.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not name:
        return {"ok": False, "error": "name is required"}
    import math
    params: dict = {"name": name}
    if emission_rate >= 0.0: params["emission_rate"] = emission_rate
    if start_lifetime > 0.0: params["start_lifetime"] = start_lifetime
    if not math.isnan(start_speed): params["start_speed"] = start_speed
    if start_size > 0.0: params["start_size"] = start_size
    if max_particles > 0: params["max_particles"] = max_particles
    if loop in (0, 1): params["loop"] = bool(loop)
    if r >= 0.0 or g >= 0.0 or b >= 0.0 or a >= 0.0:
        params["color"] = {
            "r": max(0.0, r if r >= 0.0 else 1.0),
            "g": max(0.0, g if g >= 0.0 else 1.0),
            "b": max(0.0, b if b >= 0.0 else 1.0),
            "a": max(0.0, a if a >= 0.0 else 1.0),
        }
    try:
        result = _UNITY.call("set_particle_properties", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a screen-space-overlay UI Canvas in the scene. If a Canvas with this name already exists, returns created=False and re-uses it (idempotent). Also installs an EventSystem if the scene doesn't have one. Use this first before adding any UI text or buttons.")
def unity_create_ui_canvas(name: str = "UICanvas") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not name:
        return {"ok": False, "error": "name is required"}
    try:
        result = _UNITY.call("create_ui_canvas", {"name": name})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a UI Text element under a Canvas. canvas_name='' uses the first Canvas in the scene. position is in Canvas coords (0,0 = center of canvas, +x right, +y up). Font is Unity's built-in legacy font. RGB 0-1.")
def unity_create_ui_text(
    canvas_name: str = "",
    name: str = "UIText",
    text: str = "",
    position_x: float = 0.0,
    position_y: float = 0.0,
    width: float = 400.0,
    height: float = 80.0,
    font_size: int = 36,
    r: float = 1.0,
    g: float = 1.0,
    b: float = 1.0,
    a: float = 1.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not name:
        return {"ok": False, "error": "name is required"}
    params = {
        "canvas_name": canvas_name,
        "name": name,
        "text": text,
        "position_x": position_x,
        "position_y": position_y,
        "width": width,
        "height": height,
        "font_size": font_size,
        "color": {"r": r, "g": g, "b": b, "a": a},
    }
    try:
        result = _UNITY.call("create_ui_text", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Create a UI Button under a Canvas with an Image background + Text label child. canvas_name='' uses the first Canvas in the scene. position is in Canvas coords. RGB 0-1.")
def unity_create_ui_button(
    canvas_name: str = "",
    name: str = "UIButton",
    label: str = "Button",
    position_x: float = 0.0,
    position_y: float = 0.0,
    width: float = 200.0,
    height: float = 60.0,
    font_size: int = 24,
    bg_r: float = 0.2,
    bg_g: float = 0.2,
    bg_b: float = 0.25,
    bg_a: float = 1.0,
    label_r: float = 1.0,
    label_g: float = 1.0,
    label_b: float = 1.0,
    label_a: float = 1.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not name:
        return {"ok": False, "error": "name is required"}
    params = {
        "canvas_name": canvas_name,
        "name": name,
        "label": label,
        "position_x": position_x,
        "position_y": position_y,
        "width": width,
        "height": height,
        "font_size": font_size,
        "background_color": {"r": bg_r, "g": bg_g, "b": bg_b, "a": bg_a},
        "label_color": {"r": label_r, "g": label_g, "b": label_b, "a": label_a},
    }
    try:
        result = _UNITY.call("create_ui_button", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set Unity PlayerSettings: product_name (window title + binary name), company_name (registry path on Windows), version (bundleVersion), bundle_id (applicationIdentifier — reverse-DNS like 'com.studio.game'), default screen size. Each empty/zero param is skipped. Call this BEFORE unity_build_player so the build picks up the right metadata.")
def unity_set_player_settings(
    product_name: str = "",
    company_name: str = "",
    version: str = "",
    bundle_id: str = "",
    default_width: int = 0,
    default_height: int = 0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if bundle_id and "." not in bundle_id:
        return {"ok": False, "error": f"bundle_id should be reverse-DNS (e.g. com.studio.game); got {bundle_id!r}"}
    params: dict = {}
    if product_name: params["product_name"] = product_name
    if company_name: params["company_name"] = company_name
    if version: params["version"] = version
    if bundle_id: params["bundle_id"] = bundle_id
    if default_width > 0: params["default_width"] = default_width
    if default_height > 0: params["default_height"] = default_height
    if not params:
        return {"ok": False, "error": "at least one field must be set"}
    try:
        result = _UNITY.call("set_player_settings", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Read Unity PlayerSettings: product_name, company_name, version, bundle_id, default screen size, active build target, Unity version. Read-only.")
def unity_get_player_settings() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("get_player_settings", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set PBR properties on the shared material of a named GameObject's first Renderer. metallic + smoothness are 0-1; emission_enabled toggles the _EMISSION shader keyword; emission_color + emission_intensity drive HDR emission (intensity scales the color, so emission_color=(1,0.5,0.1) at intensity=2 gives bright orange glow). Leave any param at its default to skip it. Works on URP / Built-in / HDRP through HasProperty fallback.")
def unity_set_material_pbr(
    target_name: str,
    metallic: float = -1.0,
    smoothness: float = -1.0,
    emission_enabled: int = -1,  # -1 = no change, 0 = off, 1 = on
    emission_r: float = -1.0,
    emission_g: float = -1.0,
    emission_b: float = -1.0,
    emission_intensity: float = -1.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not target_name:
        return {"ok": False, "error": "target_name is required"}
    params: dict = {"name": target_name}
    if metallic >= 0.0:
        params["metallic"] = max(0.0, min(1.0, metallic))
    if smoothness >= 0.0:
        params["smoothness"] = max(0.0, min(1.0, smoothness))
    if emission_enabled in (0, 1):
        params["emission_enabled"] = bool(emission_enabled)
    if emission_r >= 0.0 or emission_g >= 0.0 or emission_b >= 0.0:
        params["emission_color"] = {
            "r": max(0.0, emission_r if emission_r >= 0.0 else 1.0),
            "g": max(0.0, emission_g if emission_g >= 0.0 else 1.0),
            "b": max(0.0, emission_b if emission_b >= 0.0 else 1.0),
            "a": 1.0,
        }
    if emission_intensity >= 0.0:
        params["emission_intensity"] = emission_intensity
    try:
        result = _UNITY.call("set_material_pbr", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Read the current material properties of a named GameObject's first Renderer: base color, metallic, smoothness, emission state + color. Read-only — use this before set_material_pbr to know what you're changing.")
def unity_get_material_properties(target_name: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not target_name:
        return {"ok": False, "error": "target_name is required"}
    try:
        result = _UNITY.call("get_material_properties", {"name": target_name})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Configure the scene's skybox. material_path='Assets/.../sky.mat' loads a project asset; leave empty to use the procedural sky shader, which we then tune with sun_size (0..1, default 0.04), atmosphere_thickness (0..5, default 1.0), exposure (0..8, default 1.3), sky_tint and ground_color RGB. RGB 0-1.")
def unity_set_skybox(
    material_path: str = "",
    sun_size: float = 0.04,
    atmosphere_thickness: float = 1.0,
    exposure: float = 1.3,
    sky_r: float = 0.5,
    sky_g: float = 0.5,
    sky_b: float = 0.5,
    ground_r: float = 0.37,
    ground_g: float = 0.34,
    ground_b: float = 0.31,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    params: dict = {}
    if material_path:
        params["material_path"] = material_path
    else:
        params["sun_size"] = sun_size
        params["atmosphere_thickness"] = atmosphere_thickness
        params["exposure"] = exposure
        params["sky_tint"] = {"r": sky_r, "g": sky_g, "b": sky_b, "a": 1.0}
        params["ground_color"] = {"r": ground_r, "g": ground_g, "b": ground_b, "a": 1.0}
    try:
        result = _UNITY.call("set_skybox", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Configure RenderSettings fog. mode is 'Linear' / 'Exponential' / 'ExponentialSquared'. density is for Exp modes (0..1). start_distance + end_distance are for Linear mode. RGB 0-1.")
def unity_set_fog(
    enabled: int = 1,  # -1 = no change, 0 = off, 1 = on
    mode: str = "",
    density: float = -1.0,
    start_distance: float = -1.0,
    end_distance: float = -1.0,
    r: float = -1.0,
    g: float = -1.0,
    b: float = -1.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    params: dict = {}
    if enabled in (0, 1):
        params["enabled"] = bool(enabled)
    if mode:
        params["mode"] = mode
    if density >= 0.0:
        params["density"] = density
    if start_distance >= 0.0:
        params["start_distance"] = start_distance
    if end_distance >= 0.0:
        params["end_distance"] = end_distance
    if r >= 0.0 or g >= 0.0 or b >= 0.0:
        params["color"] = {
            "r": max(0.0, r if r >= 0.0 else 0.5),
            "g": max(0.0, g if g >= 0.0 else 0.5),
            "b": max(0.0, b if b >= 0.0 else 0.5),
            "a": 1.0,
        }
    try:
        result = _UNITY.call("set_fog", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Snapshot the scene's atmosphere: current skybox shader + procedural params, fog enabled / mode / density / colour, ambient intensity + mode. Read-only.")
def unity_get_atmosphere_state() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("get_atmosphere_state", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_BEHAVIOUR_LIBRARY = (
    "Rotator", "Bobber", "PulseScale", "LookAtCamera",
    "DestroyAfter", "FollowTarget", "LoadSceneOnClick",
    "QuitOnClick", "KeyboardMover", "LocalizedText",
    # Phase 40: game-loop primitives
    "GameSession", "Collectible", "ScoreHUD",
    # Phase 41: pause + persistent settings
    "PauseMenu", "SettingsStore",
    # Phase 43: combat primitives
    "Projectile", "Shooter", "Spawner", "Enemy",
    # Phase 46: endless-runner primitives
    "AutoScroller", "LanePositioner",
)


@tool(description="Attach (or reconfigure) a behaviour from the UnityTools library to a named GameObject. Behaviours are pre-built MonoBehaviour scripts that ship with the plugin: Rotator, Bobber, PulseScale, LookAtCamera, DestroyAfter, FollowTarget, LoadSceneOnClick, QuitOnClick, KeyboardMover. Pass per-behaviour fields as the params dict (e.g. params={'speedDegPerSec': 90, 'axis': {'x': 0, 'y': 1, 'z': 0}}); fields the behaviour doesn't have are reported in skipped_fields. Idempotent — re-attaching just updates the fields.")
def unity_attach_behaviour(target_name: str, behaviour_name: str, params: dict | None = None) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not target_name:
        return {"ok": False, "error": "target_name is required"}
    if not behaviour_name:
        return {"ok": False, "error": "behaviour_name is required"}
    if behaviour_name not in _BEHAVIOUR_LIBRARY:
        return {"ok": False, "error": f"unknown behaviour {behaviour_name!r}; available: {list(_BEHAVIOUR_LIBRARY)}"}
    try:
        result = _UNITY.call(
            "attach_behaviour",
            {"target_name": target_name, "behaviour_name": behaviour_name, "params": params or {}},
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List every behaviour the UnityTools plugin ships, with their public fields + types. Use this to see what's attachable before calling unity_attach_behaviour. Read-only.")
def unity_list_behaviour_library() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_behaviour_library", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List UnityTools behaviours attached in the scene. Pass target_name='' to scan the whole scene, or a specific GameObject name to scope. Read-only.")
def unity_list_attached_behaviours(target_name: str = "") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_attached_behaviours", {"target_name": target_name})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List the scenes currently in EditorBuildSettings — these are what unity_build_player will include unless overridden. Returns paths + enabled flags + active build target. Read-only.")
def unity_list_build_scenes() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_build_scenes", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Add (or update) a scene in EditorBuildSettings so the next build includes it. scene_path is a project-relative path like 'Assets/Scenes/Main.unity'. Idempotent: re-adding the same path just toggles the enabled flag.")
def unity_add_scene_to_build(scene_path: str, enabled: bool = True) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not scene_path:
        return {"ok": False, "error": "scene_path is required"}
    if not scene_path.endswith(".unity"):
        return {"ok": False, "error": f"scene_path must end in .unity; got {scene_path!r}"}
    try:
        result = _UNITY.call("add_scene_to_build", {"scene_path": scene_path, "enabled": bool(enabled)})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Build a Unity player. target is one of windows / mac / linux / webgl / android / ios (default = active build target). output_path is the absolute path to write the binary to (its parent dir is created if missing). scenes is an optional list of scene paths to override EditorBuildSettings; pass [] to use the configured build settings. development_build=True embeds the dev-mode flag. This can take minutes — the bridge call uses a long timeout.")
def unity_build_player(
    output_path: str,
    target: str = "",
    scenes: list[str] | None = None,
    development_build: bool = False,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    if not output_path:
        return {"ok": False, "error": "output_path is required"}
    params: dict = {
        "output_path": output_path,
        "target": target,
        "development_build": bool(development_build),
    }
    if scenes:
        params["scenes"] = list(scenes)
    try:
        # Builds can take many minutes. 30 min ceiling.
        result = _UNITY.call("build_player", params, timeout=1800)
        return {"ok": bool(result.get("ok", False)) if isinstance(result, dict) else False,
                **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List every UI Canvas in the scene with its Text + Button children. Also reports whether an EventSystem exists (buttons won't be clickable without one). Read-only.")
def unity_list_ui_elements() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_ui_elements", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List every ParticleSystem in the active scene with emission rate, lifetime, speed, color, and max particles. Also returns scene-total emission rate and max-particle count. Read-only — use this before adding a system to avoid duplicates.")
def unity_list_particle_systems() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_particle_systems", {})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Set camera settings on a GameObject that has a Camera component. FOV in degrees, near/far clip planes, orthographic toggle, orthographic size.")
def unity_set_camera(
    name: str,
    fov: float = 0.0,
    near_clip: float = 0.0,
    far_clip: float = 0.0,
    orthographic: bool = False,
    orthographic_size: float = 0.0,
    bg_r: float = -1.0,
    bg_g: float = -1.0,
    bg_b: float = -1.0,
    bg_a: float = -1.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        params: dict[str, object] = {"name": name}
        if fov > 0:
            params["fov"] = fov
        if near_clip > 0:
            params["near_clip"] = near_clip
        if far_clip > 0:
            params["far_clip"] = far_clip
        if orthographic_size > 0:
            params["orthographic_size"] = orthographic_size
        params["orthographic"] = orthographic
        if bg_r >= 0:
            params["background_color"] = {"r": bg_r, "g": bg_g, "b": bg_b, "a": bg_a}
        result = _UNITY.call("set_camera", params)
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Enter or exit Play mode in the Unity Editor.")
def unity_play_mode(play: bool = True) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("play_mode", {"play": play})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Instantiate a prefab from Assets folder into the scene. Path like Assets/Prefabs/MyPrefab.prefab")
def unity_instantiate_prefab(path: str, position_x: float = 0.0, position_y: float = 0.0, position_z: float = 0.0) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "instantiate_prefab",
            {
                "path": path,
                "position": {"x": position_x, "y": position_y, "z": position_z},
            },
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Instantiate multiple prefabs in one Unity RPC call to avoid timeouts. items is a list of {path, name?, position?, rotation?, scale?}.")
def unity_instantiate_prefabs(items: list[dict], max: int = 200) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("instantiate_prefabs", {"items": items, "max": max})
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Get Unity Editor busy state: compiling/updating/playmode.")
def unity_get_editor_state() -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("get_editor_state")
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Add a collider to a GameObject. collider_type can be Box, Sphere, Capsule, Mesh, Terrain.")
def unity_add_collider(name: str, collider_type: str = "Box") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("add_collider", {"name": name, "collider_type": collider_type})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Configure Rigidbody on a GameObject. Adds Rigidbody if missing. use_gravity, is_kinematic, mass, drag, angular_drag. interpolate can be None, Interpolate, Extrapolate. collision_detection can be Discrete, Continuous, ContinuousDynamic.")
def unity_set_rigidbody(
    name: str,
    use_gravity: bool = True,
    is_kinematic: bool = False,
    mass: float = 1.0,
    drag: float = 0.0,
    angular_drag: float = 0.05,
    interpolate: str = "None",
    collision_detection: str = "Discrete",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call(
            "set_rigidbody",
            {
                "name": name,
                "use_gravity": use_gravity,
                "is_kinematic": is_kinematic,
                "mass": mass,
                "drag": drag,
                "angular_drag": angular_drag,
                "interpolate": interpolate,
                "collision_detection": collision_detection,
            },
        )
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find all GameObjects with a given tag in the active scene.")
def unity_find_by_tag(tag: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("find_by_tag", {"tag": tag})
        return {"ok": True, **(result if isinstance(result, dict) else {})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find assets in the Unity project via AssetDatabase. type examples: Prefab, Material, Texture2D, Mesh, ScriptableObject, AudioClip. folders are like ['Assets/Prefabs', 'Assets/Art']")
def unity_find_assets(query: str = "", type: str = "", folders: list[str] | None = None, max_results: int = 50) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        params: dict[str, object] = {"query": query, "type": type, "max_results": max_results}
        if folders:
            params["folders"] = folders
        result = _UNITY.call("find_assets", params)
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="List prefabs under a folder (default Assets). Returns paths usable with unity_instantiate_prefab.")
def unity_list_prefabs(folder: str = "Assets", max_results: int = 200) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("list_prefabs", {"folder": folder, "max_results": max_results})
        return {"ok": True, **(result if isinstance(result, dict) else {"result": result})}
    except Exception as e:
        return {"ok": False, "error": str(e)}
