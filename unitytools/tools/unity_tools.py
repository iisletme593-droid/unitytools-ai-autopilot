"""Unity-related tools exposed to the LLM."""
from __future__ import annotations


from ..core.tool_registry import tool
from ..core.layout import compute_layout_positions, compute_structure_positions
from ..core.lighting import compute_studio_lighting_rig
from ..core.camera import frame_camera_pose
from ..core.palette import resolve_color, theme_palette
from ..core.quality import assess_qa
from ..core.security import safe_contained_path
from ..core.gameplay import plan_gameplay_behaviour, prune_redundant_steps, generate_behaviour_script, wait_until_compiled


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


# ---------------------------------------------------------------------------
# Wired bridge commands: thin wrappers over existing CommandHandlers commands
# that previously had NO Python tool, so the autopilot LLM could not reach them
# (materials/palette, semantic find/delete, scene catalog, optimized forest
# scene, visual QA, snapshots, performance profiling, LOD). Params are grounded
# in the real C# handlers in unity_plugin/Editor/Bridge/CommandHandlers.cs.
# ---------------------------------------------------------------------------


@tool(description="Apply a themed color palette (e.g. 'forest') to scene materials, recreating broken/unsupported materials and preserving textures. Optionally scope by semantic query/category.")
def unity_apply_material_palette(query: str = "", category: str = "", palette: str = "forest", max: int = 2000) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("apply_material_palette", {"query": query, "category": category, "palette": palette, "max": max}, timeout=120)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Scan scene renderers and report material problems (missing materials, broken/unsupported shaders, textured materials) without modifying anything. Optionally scope by semantic query/category.")
def unity_diagnose_material_issues(query: str = "", category: str = "", max: int = 2000) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("diagnose_material_issues", {"query": query, "category": category, "max": max}, timeout=90)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Repair scene materials by recreating missing/broken (and optionally pipeline-incompatible) materials, preserving textures and optionally tinting them with a palette.")
def unity_repair_material_issues(query: str = "", category: str = "", tint: bool = False, palette: str = "forest", include_unsupported: bool = False, max: int = 2000) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("repair_material_issues", {"query": query, "category": category, "tint": tint, "palette": palette, "include_unsupported": include_unsupported, "max": max}, timeout=180)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Normalize texture asset import settings (normal-map type, sRGB/linear, mipmaps, max size, compression) for assets matching an AssetDatabase search query.")
def unity_repair_texture_import_settings(query: str = "texture", max: int = 500) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("repair_texture_import_settings", {"query": query, "max": max}, timeout=240)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Generate a performance-optimized forest scene in Unity (terrain, pines, dead trees, rocks, fog, directional light, overview camera) from a deterministic seed.")
def unity_create_optimized_forest_scene(clear_scene: bool = True, tree_count: int = 100, rock_count: int = 18, terrain_size: float = 120.0, seed: int = 12345) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("create_optimized_forest_scene", {
            "clear_scene": clear_scene,
            "tree_count": tree_count,
            "rock_count": rock_count,
            "terrain_size": terrain_size,
            "seed": seed,
        }, timeout=180)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Return a catalog of the active Unity scene: every GameObject with its category, tag, layer, position, renderer/material/component summary, plus per-category counts. Use max_results to cap the response size.")
def unity_get_scene_catalog(max_results: int = 1000) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("get_scene_catalog", {"max_results": max_results}, timeout=60)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find GameObjects in the active Unity scene by a semantic query and/or category, returning their names, paths, categories, positions, and renderer counts.")
def unity_find_scene_objects_semantic(query: str = "", category: str = "", max_results: int = 100) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("find_scene_objects_semantic", {"query": query, "category": category, "max_results": max_results}, timeout=60)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Delete GameObjects from the active Unity scene that match a semantic query and/or category; returns the count and names of deleted objects.")
def unity_delete_scene_objects_semantic(query: str = "", category: str = "", max: int = 500) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("delete_scene_objects_semantic", {"query": query, "category": category, "max": max}, timeout=90)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Run a visual QA pass on the active Unity scene (counts objects/renderers/lights/cameras, flags missing/broken/unsupported materials, optionally captures a SceneView screenshot) and returns a verdict.")
def unity_run_visual_qa(capture_screenshot: bool = True) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("run_visual_qa", {"capture_screenshot": capture_screenshot}, timeout=120)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Save the active Unity scene and write a timestamped snapshot copy under Assets/AutopilotSnapshots/ tagged with an optional label.")
def unity_create_scene_snapshot(label: str = "manual") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("create_scene_snapshot", {"label": label}, timeout=60)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Restore a previously saved scene snapshot by opening the snapshot .unity asset (must be a path under Assets/) as the active scene.")
def unity_restore_scene_snapshot(path: str) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    # Path-traversal guard: the model picks this path, so confine it to Assets/
    # and reject absolute / drive-letter / '..'-escaping paths before the bridge
    # opens it. Legit Assets/AutopilotSnapshots/*.unity paths still pass.
    norm = str(path or "").strip().replace("\\", "/")
    if not norm.startswith("Assets/"):
        return {"ok": False, "error": "snapshot path must be under Assets/"}
    try:
        safe_contained_path("Assets", norm[len("Assets/"):])  # raises ValueError on escape
    except ValueError as e:
        return {"ok": False, "error": f"unsafe snapshot path: {e}"}
    try:
        result = _UNITY.call("restore_scene_snapshot", {"path": norm}, timeout=60)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Profile the active Unity scene's render cost: counts renderers/meshes/lights, vertex and triangle totals, shadow casters, unique materials, and returns optimization suggestions.")
def unity_profile_scene_performance(max_objects: int = 10000) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("profile_scene_performance", {"max_objects": max_objects}, timeout=120)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Speed up the Unity editor for heavy scenes: disables vSync/MSAA, turns off light and renderer shadows, and sets shadow distance and LOD bias.")
def unity_optimize_editor_performance(shadow_distance: float = 25.0, lod_bias: float = 0.55) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("optimize_editor_performance", {
            "shadow_distance": shadow_distance,
            "lod_bias": lod_bias,
        }, timeout=60)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Find heavy meshes in the scene that are good LOD/decimation candidates (e.g. repeated trees/rocks), grouped by mesh with triangle totals and per-group recommendations. Read-only analysis.")
def unity_analyze_lod_decimation_candidates(query: str = "", category: str = "", max_results: int = 25, min_triangles: int = 10000) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("analyze_lod_decimation_candidates", {
            "query": query,
            "category": category,
            "max_results": max_results,
            "min_triangles": min_triangles,
        }, timeout=120)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Apply an LOD/decimation plan to heavy meshes: adds LODGroups with proxy LODs, optionally disables shadows, marks objects static, and can replace originals with low-poly proxies. Mutates the active scene.")
def unity_apply_lod_decimation_plan(query: str = "", category: str = "tree", max_objects: int = 150, min_triangles_per_object: int = 25000, create_proxy_lods: bool = True, replace_with_proxy: bool = False, disable_shadows: bool = True, mark_static: bool = True, lod0_screen_relative_height: float = 0.38, lod1_screen_relative_height: float = 0.08) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    try:
        result = _UNITY.call("apply_lod_decimation_plan", {
            "query": query,
            "category": category,
            "max_objects": max_objects,
            "min_triangles_per_object": min_triangles_per_object,
            "create_proxy_lods": create_proxy_lods,
            "replace_with_proxy": replace_with_proxy,
            "disable_shadows": disable_shadows,
            "mark_static": mark_static,
            "lod0_screen_relative_height": lod0_screen_relative_height,
            "lod1_screen_relative_height": lod1_screen_relative_height,
        }, timeout=240)
        return result if isinstance(result, dict) else {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Run a visual-QA pass on the active scene and (optionally) auto-fix what it finds (broken/missing/unsupported materials, missing lights), then re-check. Snapshots the scene before the first fix. Returns per-pass verdicts and the fixes applied. This is the build->QA->fix quality loop.")
def unity_quality_pass(auto_fix: bool = True, max_passes: int = 2, capture_screenshot: bool = True) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    passes = max(1, min(int(max_passes), 4))
    history: list[dict] = []
    applied: list[dict] = []
    snapshotted = False
    final: dict | None = None
    try:
        for i in range(passes):
            qa = _UNITY.call("run_visual_qa", {"capture_screenshot": capture_screenshot})
            assessment = assess_qa(qa if isinstance(qa, dict) else {})
            final = assessment
            history.append({
                "pass": i,
                "passed": assessment["passed"],
                "score": assessment["score"],
                "fixes": [f["tool"] for f in assessment["fixes"]],
            })
            if assessment["passed"] or not auto_fix or not assessment["fixes"]:
                break
            # Snapshot once before mutating anything, so the fixes are reversible.
            if not snapshotted:
                snap = globals().get("unity_create_scene_snapshot")
                if callable(snap):
                    snap(label="auto_before_quality_fix")
                snapshotted = True
            for fx in assessment["fixes"]:
                fn = globals().get(fx["tool"])
                if not callable(fn):
                    continue
                res = fn(**fx.get("params", {}))
                applied.append({
                    "tool": fx["tool"],
                    "ok": bool(isinstance(res, dict) and res.get("ok", True)),
                    "reason": fx.get("reason", ""),
                })
        return {
            "ok": True,
            "passed": bool(final and final["passed"]),
            "final_score": final["score"] if final else None,
            "passes": history,
            "applied_fixes": applied,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool(description="Give a GameObject a gameplay behaviour by name: physics/falling/heavy/floaty/kinematic/static_obstacle (composes Rigidbody + collider, turning a static prop into a physics-driven game object). Scripted behaviours like rotate/patrol/follow report needs_script (await a future bridge command). The first step from decorating scenes to authoring gameplay.")
def unity_add_gameplay_behaviour(object_name: str, behaviour: str = "physics") -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    plan = plan_gameplay_behaviour(behaviour, object_name)
    if not plan.get("ok"):
        return plan

    # Idempotency: skip adding a collider if the object already has one.
    existing: list = []
    details_fn = globals().get("unity_get_object_details")
    if callable(details_fn):
        det = details_fn(object_name)
        if isinstance(det, dict):
            existing = det.get("components", []) or []
    steps, skipped = prune_redundant_steps(plan["steps"], existing)

    applied: list[dict] = []
    for step in steps:
        fn = globals().get(step["tool"])
        if not callable(fn):
            applied.append({"tool": step["tool"], "ok": False, "error": "tool unavailable"})
            continue
        res = fn(**step["kwargs"])
        applied.append({
            "tool": step["tool"],
            "ok": bool(isinstance(res, dict) and res.get("ok", True)),
            "error": res.get("error") if isinstance(res, dict) else None,
        })
    for step in skipped:
        applied.append({"tool": step["tool"], "ok": True, "skipped": True, "reason": step.get("reason")})

    return {
        "ok": all(a["ok"] for a in applied),
        "object": object_name,
        "behaviour": plan["behaviour"],
        "applied": applied,
    }


@tool(description="Generate a MonoBehaviour script for a scripted gameplay behaviour (rotate/spin/move). Returns the C# source + class name. With auto_import=True (and a live bridge) it also imports the script into Assets/AutopilotScripts so Unity compiles it; then call unity_add_component(object, <class>) AFTER the recompile finishes. Default auto_import=False (generate only — safe, no recompile).")
def unity_add_script_behaviour(object_name: str, behaviour: str = "rotate", speed: float = 0.0, auto_import: bool = False) -> dict:
    script = generate_behaviour_script(behaviour, speed=(speed or None))
    if not script.get("ok"):
        return script
    out: dict = {
        "ok": True,
        "object": object_name,
        "behaviour": script["behaviour"],
        "class_name": script["class_name"],
        "filename": script["filename"],
        "source": script["source"],
        "next_step": f"After Unity recompiles, call unity_add_component('{object_name}', '{script['class_name']}').",
        "imported": False,
    }
    if not auto_import:
        return out
    if _UNITY is None:
        out["error"] = "auto_import requested but UnityBridge is not initialized"
        return out
    import os
    import tempfile
    try:
        tmpdir = tempfile.mkdtemp()
        src_path = os.path.join(tmpdir, f"{script['class_name']}.cs")
        with open(src_path, "w", encoding="utf-8") as fh:
            fh.write(script["source"])
        imp = globals().get("unity_import_asset")
        res = imp(src_path, f"AutopilotScripts/{script['class_name']}.cs") if callable(imp) else {"ok": False, "error": "import tool unavailable"}
        out["imported"] = bool(isinstance(res, dict) and res.get("ok"))
        out["import_result"] = res
        out["note"] = "Script imported; Unity is recompiling. Add the component once compilation completes."
    except Exception as e:
        out["error"] = str(e)
    return out


@tool(description="End-to-end SCRIPTED gameplay: generate a MonoBehaviour (rotate/spin/move), import it (triggers a Unity recompile), wait for compilation to finish, then attach it to the object so it actually runs. NOTE: importing a script reloads the Unity domain — best run with the editor in focus; the bridge briefly reconnects.")
def unity_apply_script_behaviour(object_name: str, behaviour: str = "rotate", speed: float = 0.0, max_compile_wait: float = 30.0) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    imp = unity_add_script_behaviour(object_name, behaviour, speed=speed, auto_import=True)
    if not imp.get("ok"):
        return {"ok": False, "stage": "generate", **imp}
    if not imp.get("imported"):
        return {"ok": False, "stage": "import", **imp}
    class_name = imp["class_name"]

    import time
    state_fn = globals().get("unity_get_editor_state")
    attempts = max(1, int(float(max_compile_wait) / 2.0))
    compiled = wait_until_compiled(
        get_state=(state_fn if callable(state_fn) else (lambda: {})),
        sleep=time.sleep,
        max_attempts=attempts,
        interval=2.0,
    )

    add_fn = globals().get("unity_add_component")
    add_res = add_fn(object_name, class_name) if callable(add_fn) else {"ok": False, "error": "add tool unavailable"}
    return {
        "ok": bool(isinstance(add_res, dict) and add_res.get("ok")),
        "object": object_name,
        "behaviour": imp["behaviour"],
        "class_name": class_name,
        "imported": True,
        "compiled_in_time": compiled,
        "add_component": add_res,
    }


def _execute_grouped_behaviour_plan(steps: list) -> dict:
    """Build a behaviour plan against the live bridge: geometry first, then import
    each UNIQUE script once (one recompile, not one per object), wait for the
    compile, then attach the compiled component to every target. Returns
    {applied, unique_scripts}. Shared by unity_build_simple_game and
    unity_animate_group so the build->import->wait->attach path lives in one place.
    """
    from ..core.game_blueprint import group_execution_plan

    grouped = group_execution_plan(steps)
    applied: list[dict] = []

    # 1) geometry (so target objects exist before attaching)
    for step in grouped["geometry"]:
        fn = globals().get(step["tool"])
        res = fn(**step["kwargs"]) if callable(fn) else {"ok": False, "error": "tool unavailable"}
        applied.append({"step": step["tool"], "ok": bool(isinstance(res, dict) and res.get("ok", True))})

    # 2) import each UNIQUE behaviour script once (one recompile, not one per object)
    class_by_behaviour: dict[str, str] = {}
    for behaviour in grouped["script_behaviours"]:
        gen = unity_add_script_behaviour("", behaviour, auto_import=True)
        cls = gen.get("class_name")
        if cls:
            class_by_behaviour[behaviour] = cls
        applied.append({"step": f"import:{behaviour}", "ok": bool(gen.get("imported"))})

    # 3) wait for the SINGLE recompile
    import time
    state_fn = globals().get("unity_get_editor_state")
    wait_until_compiled(state_fn if callable(state_fn) else (lambda: {}), time.sleep, max_attempts=30, interval=2.0)

    # 4) attach the compiled component to each target object
    add_fn = globals().get("unity_add_component")
    for att in grouped["attachments"]:
        cls = class_by_behaviour.get(att["behaviour"])
        if not cls or not callable(add_fn):
            applied.append({"step": f"attach:{att['behaviour']}->{att['object']}", "ok": False, "error": "class unavailable"})
            continue
        res = add_fn(att["object"], cls)
        applied.append({"step": f"attach:{cls}->{att['object']}", "ok": bool(isinstance(res, dict) and res.get("ok", True))})

    return {"applied": applied, "unique_scripts": len(grouped["script_behaviours"])}


@tool(description="Plan (and optionally build) a simple PLAYABLE game from the gameplay building blocks. game_type='collectathon'/'dodge'/'survival'/'platformer'/'chase'. collectible_count is the count of the main repeated element. An optional seed makes the layout reproducibly varied (same seed -> same game). execute=False (default) returns the step plan without touching the scene; execute=True builds the geometry and imports the behaviour scripts (triggers Unity recompiles, so run with the editor in focus).")
def unity_build_simple_game(collectible_count: int = 5, execute: bool = False, game_type: str = "collectathon", seed: str = "") -> dict:
    from ..core.game_blueprint import plan_game
    plan = plan_game(game_type, collectible_count, seed=seed or None)
    if not execute:
        return {
            "ok": True,
            "dry_run": True,
            **plan,
            "note": "execute=False: plan only, no scene changes. Set execute=True to build (script behaviours trigger Unity recompiles).",
        }
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}

    result = _execute_grouped_behaviour_plan(plan["steps"])
    applied = result["applied"]
    return {
        "ok": all(a["ok"] for a in applied),
        "game": plan["game"],
        "executed": True,
        "unique_scripts": result["unique_scripts"],
        "applied": applied,
    }


@tool(description="Compose a CUSTOM game from a described element MIX instead of a preset blueprint: choose how many enemies/collectibles/hazards plus optional goal and timer, and it assembles a valid, playable plan from the same building blocks, wiring the sensible couplings (enemies -> player gets health+attack + a win/lose manager; collectibles/enemies -> a score HUD; timer -> outlast-the-clock win). For 'kendi oyununu tarif et / ozel oyun / custom game: 1 player, 5 enemies, 3 collectibles, a timer'. execute=False (default) returns the plan + assessment without touching the scene; execute=True builds it (script behaviours trigger Unity recompiles).")
def unity_compose_game(player: bool = True, enemy: int = 0, collectible: int = 0,
                       hazard: int = 0, goal: bool = False, timer: bool = False,
                       spawner: int = 0, ranged: bool = False, guard: int = 0,
                       crate: int = 0, moving_hazard: int = 0, turret: int = 0,
                       deadline: bool = False, seed: str = "",
                       execute: bool = False) -> dict:
    from ..core.game_blueprint import compose_custom_game
    from ..core.game_qa import assess_game_readiness
    plan = compose_custom_game(player=player, enemy=enemy, collectible=collectible,
                               hazard=hazard, goal=goal, timer=timer, spawner=spawner,
                               ranged=ranged, guard=guard, crate=crate,
                               moving_hazard=moving_hazard, turret=turret, deadline=deadline,
                               seed=seed or None)
    if not execute:
        return {
            "ok": True,
            "dry_run": True,
            **plan,
            "assessment": assess_game_readiness(plan),
            "note": "execute=False: plan only, no scene changes. Set execute=True to build (script behaviours trigger Unity recompiles).",
        }
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    result = _execute_grouped_behaviour_plan(plan["steps"])
    applied = result["applied"]
    return {
        "ok": all(a["ok"] for a in applied),
        "game": plan["game"],
        "spec": plan["spec"],
        "executed": True,
        "unique_scripts": result["unique_scripts"],
        "applied": applied,
    }


@tool(description="Bring a scene to life: place N props (Sphere/Cube/...) and give each a DECORATIVE scripted behaviour (bob/orbit/rotate/wander, cycled) so the scene breathes — juice, not a game (no player/goal). behaviours is an optional comma-separated subset (e.g. 'bob,rotate'). execute=False (default) returns the step plan without touching the scene; execute=True builds it and imports the scripts (triggers a Unity recompile, so run with the editor in focus). 'sahneyi canlandir', 'yasayan sahne', 'animate the scene'.")
def unity_animate_group(
    count: int = 8,
    primitive: str = "Sphere",
    pattern: str = "circle",
    arena_size: float = 16.0,
    behaviours: str = "",
    execute: bool = False,
) -> dict:
    from ..core.game_blueprint import plan_ambient_decor
    beh_list = [b.strip() for b in behaviours.split(",") if b.strip()] or None
    plan = plan_ambient_decor(
        count=count, arena_size=arena_size, primitive=primitive, pattern=pattern, behaviours=beh_list
    )
    if not execute:
        return {
            "ok": True,
            "dry_run": True,
            **plan,
            "note": "execute=False: plan only, no scene changes. Set execute=True to build (script behaviours trigger a Unity recompile).",
        }
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}

    result = _execute_grouped_behaviour_plan(plan["steps"])
    applied = result["applied"]
    return {
        "ok": all(a["ok"] for a in applied),
        "decor": plan["decor"],
        "executed": True,
        "unique_scripts": result["unique_scripts"],
        "applied": applied,
    }


@tool(description="Assess a game blueprint WITHOUT touching the scene (pure analysis, no bridge): how many objects and behaviours it has, whether it has a player/goal/score, and whether it is actually playable. game_type='collectathon'/'dodge'/'survival'/'platformer'/'chase'. Returns counts + a playable verdict + warnings (e.g. 'no goal'). Use to sanity-check a game before building it.")
def unity_assess_game(game_type: str = "collectathon", collectible_count: int = 5) -> dict:
    from ..core.game_blueprint import plan_game
    from ..core.game_qa import assess_game_readiness
    plan = plan_game(game_type, collectible_count)
    report = assess_game_readiness(plan)
    report["summary"] = plan.get("summary", "")
    return report


@tool(description="Generate several difficulty variations of ONE game type WITHOUT touching the scene (pure, no bridge): same game at different counts (easy/medium/hard) each with a readiness summary. game_type='collectathon'/'dodge'/'survival'/'platformer'/'chase'. counts is an optional comma-separated list (e.g. '3,5,8'); empty uses the default. Use to offer the user difficulty options before building.")
def unity_game_variations(game_type: str = "collectathon", counts: str = "", arena_size: float = 20.0) -> dict:
    from ..core.game_blueprint import plan_game_variations
    count_list = [int(c) for c in counts.replace(" ", "").split(",") if c.strip().isdigit()] or None
    return plan_game_variations(game_type, counts=count_list, arena_size=arena_size)


@tool(description="Plan a multi-level CAMPAIGN of one game type WITHOUT touching the scene (pure, no bridge): an ordered sequence of `levels` levels at climbing difficulty (element count 2,4,6,...), each a full playable level with a difficulty label and a readiness check. Build a level with unity_build_simple_game(game_type, count). For 'X kampanyasi', '3 seviyeli arena'. seed makes each level reproducibly varied. Returns {ok, kind:'campaign', game_type, level_count, all_playable, levels:[{level,label,count,summary,playable,design_notes}]}.")
def unity_plan_campaign(game_type: str = "collectathon", levels: int = 3, seed: str = "") -> dict:
    from ..core.game_blueprint import plan_campaign
    result = plan_campaign(game_type, levels=levels, seed=seed or None)
    # return a lean, glanceable view (drop each level's full step plan)
    lean = {k: v for k, v in result.items() if k != "levels"}
    lean["levels"] = [{k: v for k, v in lv.items() if k != "plan"} for lv in result["levels"]]
    return lean


@tool(description="List every game the studio can make, at a glance, WITHOUT touching the scene (pure, no bridge): each game type's summary, object/script counts, playable verdict, and warnings, plus the full set of behaviours used. A 'what can I build?' report. Use to answer 'hangi oyunlar / what games can you make'.")
def unity_game_catalog(count: int = 5) -> dict:
    from ..core.game_qa import summarize_catalog
    return summarize_catalog(count)


@tool(description="Describe the whole studio in one comprehensive, code-derived report WITHOUT touching the scene (pure, no bridge): all game types + summaries, the behaviour catalog by category (scripted + physics), which games have title/win-lose/sound, persistence, procedural/seeded determinism, and the registered tool count. Everything is read from the live registries so it never drifts. Use to answer 'studio raporu / neler yapabilirsin / what can you do / capabilities'. Returns {ok, report} (markdown).")
def unity_studio_report() -> dict:
    from ..core.game_qa import build_studio_report
    return {"ok": True, "report": build_studio_report()}


@tool(description="Run a self-audit of the whole studio WITHOUT touching the scene (pure, no bridge): build every game type AND a representative matrix of composed games, and check each is VALID (whitelisted tools, no path traversal), PLAYABLE (a player + something to do), and COHERENT (passes the design critique). Use to answer 'studio sagligi / saglik denetimi / studio health / is everything healthy'. Returns {ok, blueprints:{...}, composer:{...}, all_ok} -- flagged lists are empty when everything is clean.")
def unity_studio_health() -> dict:
    from ..core.game_qa import studio_health, compose_health
    bp = studio_health()
    comp = compose_health()
    all_ok = all(bp[k] for k in ("all_valid", "all_playable", "all_coherent")) and \
        all(comp[k] for k in ("all_valid", "all_playable", "all_coherent"))
    return {"ok": True, "all_ok": all_ok, "blueprints": bp, "composer": comp}


@tool(description="Describe the freeform game COMPOSER WITHOUT touching the scene (pure, no bridge): the element types you can mix into a custom game (enemies/collectibles/hazards/spawners/guards/crates + goal/timer/ranged flags), their trigger words, and the automatic couplings that keep a mix coherent. Code-derived from the live spec parser. Use to answer 'composer raporu / ne tarif edebilirim / what can i compose / custom oyun ogeleri'. Returns {ok, report} (markdown).")
def unity_composer_report() -> dict:
    from ..core.game_studio_actions import build_composer_report
    return {"ok": True, "report": build_composer_report()}


@tool(description="Show a code-derived GAME SHOWCASE WITHOUT touching the scene (pure, no bridge): for every game type, the example natural-language prompt that builds it (each verified LIVE to route to that game), a one-line pitch, and its object count. A 'say this -> get this game' discovery gallery; the example->build routing is self-checked so it never drifts. Use to answer 'ornek oyunlar / ornek goster / show me examples / game examples / what should i type'. Returns {ok, showcase (markdown), all_route}.")
def unity_game_showcase() -> dict:
    from ..core.game_qa import build_game_showcase, showcase_routing
    return {"ok": True, "showcase": build_game_showcase(), "all_route": showcase_routing()["all_route"]}


@tool(description="Break down ONE game type in depth WITHOUT touching the scene (pure, no bridge): its size (object + unique-script counts), behaviours grouped by category (control/movement/world/combat/progression/game feel/physics), the build phases (geometry -> import unique scripts -> attach), the playability verdict + any design notes, and the example prompt that builds it. The 'zoom in on one game' counterpart to the catalog. Use to answer 'arena oyununun yapisi / X oyunu anatomisi / breakdown of the X game / X neyden olusuyor'. game_type='arena'/'maze'/'twin_stick'/... Returns {ok, game_type, anatomy (markdown)}.")
def unity_game_anatomy(game_type: str = "collectathon", count: int = 4) -> dict:
    from ..core.game_qa import build_game_anatomy
    from ..core.game_blueprint import BLUEPRINTS
    gt = game_type if game_type in BLUEPRINTS else "collectathon"
    return {"ok": True, "game_type": gt, "anatomy": build_game_anatomy(gt, count)}


@tool(description="Explain HOW TO PLAY one game type WITHOUT touching the scene (pure, no bridge): a player-facing card with the controls (WASD/jump/auto-aim/...), how to win, what to watch out for (the threats), and how to lose -- all DERIVED from the game's actual behaviours, so it matches what the game contains and never drifts. The player-facing counterpart to the (technical) anatomy. Use to answer 'X oyunu nasil oynanir / how to play the X game / X oyunu kontrolleri'. game_type='arena'/'maze'/'twin_stick'/... Returns {ok, game_type, howto (markdown)}.")
def unity_game_howto(game_type: str = "collectathon", count: int = 4) -> dict:
    from ..core.game_qa import build_game_howto
    from ..core.game_blueprint import BLUEPRINTS
    gt = game_type if game_type in BLUEPRINTS else "collectathon"
    return {"ok": True, "game_type": gt, "howto": build_game_howto(gt, count)}


@tool(description="Show which Cloudflare Workers AI models the studio routes between and how (pure, no bridge): the task->model catalog (reasoning/general/coding/creative/fast + vision/image), which support tool-calling, and how a model is chosen per turn (auto-detect + chat override). Use to answer 'hangi modeller var / model raporu / which models / model routing'. Returns {ok, report} (markdown).")
def unity_model_report() -> dict:
    from ..core.model_router import build_model_router_report, list_models
    return {"ok": True, "report": build_model_router_report(), "models": list_models()}


@tool(description="Export a game as portable, versioned JSON WITHOUT touching the scene (pure, no bridge): serialize a game_type's plan so it can be saved, shared, or replayed later. game_type='collectathon'/'dodge'/'survival'/'platformer'/'chase'. Returns {ok, game_type, json, step_count}. The JSON round-trips back via the game_io loader.")
def unity_export_game(game_type: str = "collectathon", collectible_count: int = 5, pretty: bool = True) -> dict:
    from ..core.game_blueprint import plan_game
    from ..core.game_io import serialize_plan
    plan = plan_game(game_type, collectible_count)
    text = serialize_plan(plan, pretty=pretty)
    return {"ok": True, "game_type": plan.get("game", game_type), "step_count": len(plan.get("steps", [])), "json": text}


@tool(description="Save a game to disk as JSON so it can be loaded later (no scene change, no bridge). Plans game_type at collectible_count and writes it under the saved-games directory as <name>.json (name sanitized to letters/numbers/-/_; path-traversal-guarded). game_type='collectathon'/'dodge'/'survival'/'platformer'/'chase'. name defaults to the game type. Returns {ok, name, path, step_count}.")
def unity_save_game(game_type: str = "collectathon", name: str = "", collectible_count: int = 5) -> dict:
    from ..core.game_blueprint import plan_game
    from ..core.game_io import save_plan_to_file
    plan = plan_game(game_type, collectible_count)
    try:
        return save_plan_to_file(plan, name or plan.get("game", game_type))
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e)}


@tool(description="Save a CUSTOM (composed) game to disk as JSON so it can be reloaded and built later (no scene change, no bridge): composes the described element mix (same args as unity_compose_game) and writes it under the saved-games directory as <name>.json (name sanitized; path-traversal-guarded). This is how a freeform 'ozel oyunu X olarak kaydet' creation is kept. Returns {ok, name, path, step_count} or {ok: False, error}.")
def unity_save_composed_game(name: str = "", player: bool = True, enemy: int = 0,
                             collectible: int = 0, hazard: int = 0, goal: bool = False,
                             timer: bool = False, spawner: int = 0, ranged: bool = False,
                             guard: int = 0, crate: int = 0, moving_hazard: int = 0,
                             turret: int = 0, deadline: bool = False, seed: str = "") -> dict:
    from ..core.game_blueprint import compose_custom_game
    from ..core.game_io import save_plan_to_file
    plan = compose_custom_game(player=player, enemy=enemy, collectible=collectible,
                               hazard=hazard, goal=goal, timer=timer, spawner=spawner,
                               ranged=ranged, guard=guard, crate=crate,
                               moving_hazard=moving_hazard, turret=turret, deadline=deadline,
                               seed=seed or None)
    try:
        return save_plan_to_file(plan, name or "custom")
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e)}


@tool(description="Save a whole multi-level CAMPAIGN to disk (no scene change, no bridge): plans an increasing-difficulty campaign of `levels` levels of game_type and writes each level as <name>_L1.json .. <name>_LN.json (names sanitized; path-traversal-guarded), so the progression can be reloaded and built level by level. For 'X kampanyasini Y olarak kaydet'. Returns {ok, name, game_type, level_count, saved:[names]} or {ok: False, error}.")
def unity_save_campaign(game_type: str = "collectathon", levels: int = 3,
                        name: str = "", seed: str = "") -> dict:
    from ..core.game_blueprint import plan_campaign
    from ..core.game_io import save_plan_to_file
    camp = plan_campaign(game_type, levels=levels, seed=seed or None)
    base = name or f"{camp['game_type']}_campaign"
    saved = []
    try:
        for lv in camp["levels"]:
            res = save_plan_to_file(lv["plan"], f"{base}_L{lv['level']}")
            saved.append(res["name"])
    except (ValueError, OSError) as e:
        return {"ok": False, "error": str(e), "saved": saved}
    return {"ok": True, "name": base, "game_type": camp["game_type"],
            "level_count": camp["level_count"], "saved": saved}


@tool(description="Load a previously saved game from disk by name (no scene change, no bridge): returns its PLAN only (does not build it — call unity_build_simple_game/the executor to build). Returns {ok, plan, game, step_count} or {ok: False, error}.")
def unity_load_game(name: str = "") -> dict:
    from ..core.game_io import load_plan_from_file
    try:
        plan = load_plan_from_file(name)
    except (ValueError, FileNotFoundError, OSError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "plan": plan, "game": plan.get("game") or plan.get("decor"), "step_count": len(plan.get("steps", []))}


@tool(description="List the names of all games saved to disk (no scene change, no bridge). Returns {ok, games:[names], count}.")
def unity_list_saved_games() -> dict:
    from ..core.game_io import list_saved_games
    names = list_saved_games()
    return {"ok": True, "games": names, "count": len(names)}


@tool(description="Import a game from external JSON text and validate it WITHOUT building it (pure, no bridge): parses the envelope and checks every step is a whitelisted tool call or a real templated behaviour, so a tampered/hostile file cannot make the studio call arbitrary tools. Returns {ok, plan, game, step_count} if valid, else {ok: False, error}. Build it with unity_build_loaded_game (after saving) once trusted.")
def unity_import_game(json_text: str) -> dict:
    from ..core.game_io import deserialize_plan, validate_plan
    try:
        plan = deserialize_plan(json_text)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    verdict = validate_plan(plan)
    if not verdict["ok"]:
        out = {"ok": False, "error": "invalid plan: " + verdict["error"]}
        if "index" in verdict:
            out["index"] = verdict["index"]
        return out
    return {"ok": True, "plan": plan, "game": plan.get("game") or plan.get("decor"), "step_count": verdict["step_count"]}


@tool(description="Build a previously SAVED game by name. Loads it, re-validates the plan (defense in depth), then builds it. execute=False (default) validates and returns the plan WITHOUT touching the scene; execute=True builds the geometry and imports the behaviour scripts (triggers a Unity recompile — run with the editor in focus). Returns the build report or {ok: False, error}.")
def unity_build_loaded_game(name: str = "", execute: bool = False) -> dict:
    from ..core.game_io import load_plan_from_file, validate_plan
    try:
        plan = load_plan_from_file(name)
    except (ValueError, FileNotFoundError, OSError) as e:
        return {"ok": False, "error": str(e)}
    verdict = validate_plan(plan)
    if not verdict["ok"]:
        return {"ok": False, "error": "invalid saved plan: " + verdict["error"]}
    game = plan.get("game") or plan.get("decor")
    if not execute:
        return {
            "ok": True,
            "dry_run": True,
            "game": game,
            "step_count": verdict["step_count"],
            "note": "execute=False: validated plan only, not built. Set execute=True to build (triggers a Unity recompile).",
        }
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    result = _execute_grouped_behaviour_plan(plan["steps"])
    applied = result["applied"]
    return {
        "ok": all(a["ok"] for a in applied),
        "game": game,
        "executed": True,
        "unique_scripts": result["unique_scripts"],
        "applied": applied,
    }
