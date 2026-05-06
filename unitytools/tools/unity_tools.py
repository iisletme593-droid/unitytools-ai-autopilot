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
