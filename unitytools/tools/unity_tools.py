"""Unity-related tools exposed to the LLM."""
from __future__ import annotations


from ..core.tool_registry import tool
from ..core.layout import compute_layout_positions, compute_structure_positions
from ..core.lighting import compute_studio_lighting_rig
from ..core.camera import frame_camera_pose
from ..core.palette import resolve_color, theme_palette


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


@tool(description="Place N primitives in a layout (pattern: grid/circle/line/scatter) to quickly block out a scene/level. type is Cube/Sphere/Cylinder/Capsule/Plane/Quad.")
def unity_place_primitives(
    type: str,
    count: int,
    pattern: str = "grid",
    spacing: float = 2.0,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    origin_z: float = 0.0,
    jitter: float = 0.0,
    name_prefix: str = "",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    count = max(0, min(int(count), 500))  # guvenlik tavani: asiri nesne olusturmayi engelle
    if count == 0:
        return {"ok": False, "error": "count >= 1 olmali"}
    positions = compute_layout_positions(
        count,
        pattern=pattern,
        spacing=spacing,
        origin=(origin_x, origin_y, origin_z),
        jitter=jitter,
    )
    prefix = name_prefix or type
    created: list[str] = []
    errors: list[str] = []
    for i, (x, y, z) in enumerate(positions):
        try:
            res = _UNITY.call(
                "create_primitive",
                {"type": type, "name": f"{prefix}_{i}", "position": {"x": x, "y": y, "z": z}},
            )
            created.append(res.get("name", f"{prefix}_{i}") if isinstance(res, dict) else f"{prefix}_{i}")
        except Exception as e:
            errors.append(str(e))
    return {
        "ok": len(errors) == 0,
        "created_count": len(created),
        "requested_count": count,
        "pattern": pattern,
        "errors": errors[:5],
    }


@tool(description="Build a simple structure from primitives to block out a level: kind=wall/tower/stairs/room/floor. Dimensions (width/height/depth) are in blocks. prim_type is Cube/Sphere/etc.")
def unity_build_structure(
    kind: str = "wall",
    width: int = 5,
    height: int = 3,
    depth: int = 1,
    spacing: float = 1.0,
    prim_type: str = "Cube",
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    origin_z: float = 0.0,
    name_prefix: str = "",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    positions = compute_structure_positions(
        kind,
        width=width,
        height=height,
        depth=depth,
        spacing=spacing,
        origin=(origin_x, origin_y, origin_z),
    )
    if len(positions) > 500:  # guvenlik tavani: asiri nesne olusturmayi engelle
        positions = positions[:500]
    prefix = name_prefix or f"{kind}_{prim_type}"
    created: list[str] = []
    errors: list[str] = []
    for i, (x, y, z) in enumerate(positions):
        try:
            _UNITY.call(
                "create_primitive",
                {"type": prim_type, "name": f"{prefix}_{i}", "position": {"x": x, "y": y, "z": z}},
            )
            created.append(f"{prefix}_{i}")
        except Exception as e:
            errors.append(str(e))
    return {
        "ok": len(errors) == 0,
        "kind": kind,
        "created_count": len(created),
        "requested_count": len(positions),
        "errors": errors[:5],
    }


@tool(description="Set up a studio 3-point lighting rig (key/fill/rim) around a target point for a presentable scene.")
def unity_setup_studio_lighting(
    target_x: float = 0.0,
    target_y: float = 0.0,
    target_z: float = 0.0,
    distance: float = 6.0,
    key_intensity: float = 1.3,
    name_prefix: str = "StudioLight",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    rig = compute_studio_lighting_rig(
        target=(target_x, target_y, target_z),
        distance=distance,
        key_intensity=key_intensity,
    )
    created: list[str] = []
    errors: list[str] = []
    for spec in rig:
        x, y, z = spec["position"]
        try:
            _UNITY.call(
                "create_light",
                {
                    "name": f"{name_prefix}_{spec['role']}",
                    "light_type": spec["type"],
                    "position": {"x": x, "y": y, "z": z},
                    "intensity": spec["intensity"],
                },
            )
            created.append(spec["role"])
        except Exception as e:
            errors.append(str(e))
    return {"ok": len(errors) == 0, "lights": created, "errors": errors[:5]}


@tool(description="Frame the camera on a target point (orbit by distance/yaw/pitch) for a presentable shot. camera_name defaults to 'Main Camera'; set fov>0 to also adjust field of view.")
def unity_frame_camera(
    target_x: float = 0.0,
    target_y: float = 0.0,
    target_z: float = 0.0,
    distance: float = 10.0,
    yaw_deg: float = 30.0,
    pitch_deg: float = 20.0,
    fov: float = 0.0,
    camera_name: str = "Main Camera",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    (px, py, pz), (rx, ry, rz) = frame_camera_pose(
        (target_x, target_y, target_z), distance=distance, yaw_deg=yaw_deg, pitch_deg=pitch_deg
    )
    errors: list[str] = []
    try:
        _UNITY.call("set_transform", {"name": camera_name, "position": {"x": px, "y": py, "z": pz}})
        _UNITY.call("set_transform", {"name": camera_name, "rotation": {"x": rx, "y": ry, "z": rz}})
        if fov > 0:
            _UNITY.call("set_camera", {"name": camera_name, "fov": fov})
    except Exception as e:
        errors.append(str(e))
    return {
        "ok": len(errors) == 0,
        "camera": camera_name,
        "position": [px, py, pz],
        "rotation": [rx, ry, rz],
        "errors": errors,
    }


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
        result = _UNITY.call("save_scene")
        if isinstance(result, dict) and result.get("ok") is False:
            return {
                "ok": False,
                "error": "Sahne kaydedilemedi (EditorSceneManager.SaveScene false dondu).",
                "path": result.get("path"),
            }
        return {"ok": True, "path": result.get("path") if isinstance(result, dict) else None}
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


@tool(description="Set a GameObject's material color by a color NAME (red/kirmizi/blue/mavi/gold/...), hex (#RRGGBB), or 'r,g,b'. Friendlier than raw RGB numbers.")
def unity_set_object_color(name: str, color: str = "gray") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    r, g, b = resolve_color(color)
    try:
        _UNITY.call("set_material_color", {"name": name, "r": r, "g": g, "b": b, "a": 1.0})
        return {"ok": True, "name": name, "rgb": [round(r, 3), round(g, 3), round(b, 3)]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Color a group of objects named '<prefix>_0..<prefix>_<count-1>' with a theme palette (fantasy/nature/warm/cool/mono), cycling colors. Pairs with unity_place_primitives / unity_build_structure.")
def unity_color_group(name_prefix: str, count: int, theme: str = "fantasy") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    count = max(0, min(int(count), 500))
    palette = theme_palette(theme)
    colored = 0
    errors: list[str] = []
    for i in range(count):
        r, g, b = palette[i % len(palette)]
        try:
            _UNITY.call("set_material_color", {"name": f"{name_prefix}_{i}", "r": r, "g": g, "b": b, "a": 1.0})
            colored += 1
        except Exception as e:
            errors.append(str(e))
    return {"ok": len(errors) == 0, "theme": theme, "colored_count": colored, "errors": errors[:5]}


@tool(description="Block out a small presentable scene in one shot: a floor, scattered props, studio lighting, and a framed camera. Gets from an empty scene to a composed one quickly.")
def unity_blockout_scene(
    prim_type: str = "Cube",
    floor_size: int = 8,
    prop_count: int = 6,
    spacing: float = 1.0,
    add_lighting: bool = True,
    frame_camera: bool = True,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    steps = {"floor": 0, "props": 0, "lights": 0, "camera": False}
    errors: list[str] = []
    floor_size = max(1, min(int(floor_size), 17))  # cap 17x17 = 289 floor cubes
    center = (floor_size * spacing / 2.0, 0.0, floor_size * spacing / 2.0)

    floor = compute_structure_positions("floor", width=floor_size, depth=floor_size, spacing=spacing)
    for i, (x, y, z) in enumerate(floor):
        try:
            _UNITY.call("create_primitive", {"type": "Cube", "name": f"Floor_{i}", "position": {"x": x, "y": y - 0.5, "z": z}})
            steps["floor"] += 1
        except Exception as e:
            errors.append(str(e))
            break

    props = compute_layout_positions(
        max(0, min(int(prop_count), 50)), "scatter", spacing=spacing * 1.5,
        origin=(center[0], 0.5, center[2]), seed=7,
    )
    for i, (x, y, z) in enumerate(props):
        try:
            _UNITY.call("create_primitive", {"type": prim_type, "name": f"Prop_{i}", "position": {"x": x, "y": y, "z": z}})
            steps["props"] += 1
        except Exception as e:
            errors.append(str(e))
            break

    if add_lighting:
        for spec in compute_studio_lighting_rig(target=center, distance=floor_size * spacing):
            x, y, z = spec["position"]
            try:
                _UNITY.call("create_light", {"name": f"Light_{spec['role']}", "light_type": spec["type"], "position": {"x": x, "y": y, "z": z}, "intensity": spec["intensity"]})
                steps["lights"] += 1
            except Exception as e:
                errors.append(str(e))
                break

    if frame_camera:
        (px, py, pz), (rx, ry, rz) = frame_camera_pose(center, distance=floor_size * spacing * 1.4, yaw_deg=35.0, pitch_deg=25.0)
        try:
            _UNITY.call("set_transform", {"name": "Main Camera", "position": {"x": px, "y": py, "z": pz}})
            _UNITY.call("set_transform", {"name": "Main Camera", "rotation": {"x": rx, "y": ry, "z": rz}})
            steps["camera"] = True
        except Exception as e:
            errors.append(str(e))

    return {"ok": len(errors) == 0, "steps": steps, "errors": errors[:5]}


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
