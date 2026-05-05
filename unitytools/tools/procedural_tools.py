"""Procedural / generative Unity tools that orchestrate multiple primitives
into patterns (grid, circle, scatter, stairs, walls).

These call the bridge directly to emit batches of create+transform commands.
"""
from __future__ import annotations

import math
import random
from typing import Any

from ..core.tool_registry import tool

_UNITY = None  # type: ignore


def _create_primitive(type_: str, name: str, x: float, y: float, z: float) -> dict[str, Any]:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    return _UNITY.call(
        "create_primitive",
        {
            "type": type_,
            "name": name,
            "position": {"x": x, "y": y, "z": z},
        },
    )


def _set_scale(name: str, sx: float, sy: float, sz: float) -> dict[str, Any]:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    return _UNITY.call("set_transform", {"name": name, "scale": {"x": sx, "y": sy, "z": sz}})


def _set_rotation(name: str, rx: float, ry: float, rz: float) -> dict[str, Any]:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    return _UNITY.call("set_transform", {"name": name, "rotation": {"x": rx, "y": ry, "z": rz}})


def _set_material_color(name: str, r: float, g: float, b: float, a: float = 1.0) -> dict[str, Any]:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    return _UNITY.call("set_material_color", {"name": name, "r": r, "g": g, "b": b, "a": a})


@tool(description="Create a grid of primitives. type can be Cube, Sphere, Cylinder, Capsule, Plane, Quad.")
def unity_create_grid(
    type: str = "Cube",
    rows: int = 3,
    columns: int = 3,
    spacing_x: float = 2.0,
    spacing_z: float = 2.0,
    base_name: str = "GridObj",
    start_x: float = 0.0,
    start_y: float = 0.0,
    start_z: float = 0.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    created: list[dict[str, Any]] = []
    errors: list[str] = []
    for r in range(rows):
        for c in range(columns):
            name = f"{base_name}_{r}_{c}"
            x = start_x + c * spacing_x
            z = start_z + r * spacing_z
            try:
                res = _create_primitive(type, name, x, start_y, z)
                created.append({"name": name, "result": res})
            except Exception as e:
                errors.append(f"{name}: {e}")
    return {"ok": len(errors) == 0, "created_count": len(created), "errors": errors, "objects": [o["name"] for o in created]}


@tool(description="Create primitives arranged in a circle. type can be Cube, Sphere, Cylinder, Capsule, Plane, Quad.")
def unity_create_circle_array(
    type: str = "Cube",
    count: int = 8,
    radius: float = 5.0,
    base_name: str = "CircleObj",
    center_x: float = 0.0,
    center_y: float = 0.0,
    center_z: float = 0.0,
    face_center: bool = True,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    created: list[dict[str, Any]] = []
    errors: list[str] = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        x = center_x + math.cos(angle) * radius
        z = center_z + math.sin(angle) * radius
        name = f"{base_name}_{i}"
        try:
            res = _create_primitive(type, name, x, center_y, z)
            created.append({"name": name, "result": res})
            if face_center:
                ry = -math.degrees(angle) + 90
                try:
                    _set_rotation(name, 0.0, ry, 0.0)
                except Exception:
                    pass
        except Exception as e:
            errors.append(f"{name}: {e}")
    return {"ok": len(errors) == 0, "created_count": len(created), "errors": errors, "objects": [o["name"] for o in created]}


@tool(description="Scatter primitives randomly inside a rectangular area.")
def unity_scatter_objects(
    type: str = "Cube",
    count: int = 10,
    center_x: float = 0.0,
    center_y: float = 0.0,
    center_z: float = 0.0,
    range_x: float = 10.0,
    range_y: float = 0.0,
    range_z: float = 10.0,
    min_scale: float = 0.5,
    max_scale: float = 1.5,
    base_name: str = "ScatterObj",
    seed: int = 0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    rng = random.Random(seed)
    created: list[dict[str, Any]] = []
    errors: list[str] = []
    for i in range(count):
        x = center_x + rng.uniform(-range_x / 2, range_x / 2)
        y = center_y + rng.uniform(-range_y / 2, range_y / 2) if range_y > 0 else center_y
        z = center_z + rng.uniform(-range_z / 2, range_z / 2)
        name = f"{base_name}_{i}"
        try:
            res = _create_primitive(type, name, x, y, z)
            sx = rng.uniform(min_scale, max_scale)
            sy = sx if range_y > 0 else rng.uniform(min_scale, max_scale)
            sz = sx if range_y > 0 else rng.uniform(min_scale, max_scale)
            try:
                _set_scale(name, sx, sy, sz)
            except Exception:
                pass
            created.append({"name": name, "result": res})
        except Exception as e:
            errors.append(f"{name}: {e}")
    return {"ok": len(errors) == 0, "created_count": len(created), "errors": errors, "objects": [o["name"] for o in created]}


@tool(description="Create a stairway using scaled cubes.")
def unity_create_stairs(
    steps: int = 10,
    step_width: float = 2.0,
    step_depth: float = 1.0,
    step_height: float = 0.5,
    start_x: float = 0.0,
    start_y: float = 0.0,
    start_z: float = 0.0,
    direction: str = "x",
    base_name: str = "Stair",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    created: list[dict[str, Any]] = []
    errors: list[str] = []
    for i in range(steps):
        name = f"{base_name}_{i}"
        if direction.lower() == "x":
            x = start_x + i * step_depth
            z = start_z
        else:
            x = start_x
            z = start_z + i * step_depth
        y = start_y + i * step_height
        try:
            res = _create_primitive("Cube", name, x, y, z)
            _set_scale(name, step_width if direction.lower() == "z" else step_depth, step_height, step_width if direction.lower() == "x" else step_depth)
            created.append({"name": name, "result": res})
        except Exception as e:
            errors.append(f"{name}: {e}")
    return {"ok": len(errors) == 0, "created_count": len(created), "errors": errors, "objects": [o["name"] for o in created]}


@tool(description="Create a wall from scaled cubes. Segments determine how many blocks.")
def unity_create_wall(
    length: float = 10.0,
    height: float = 3.0,
    thickness: float = 0.5,
    segments: int = 5,
    start_x: float = 0.0,
    start_y: float = 0.0,
    start_z: float = 0.0,
    direction: str = "x",
    base_name: str = "Wall",
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    created: list[dict[str, Any]] = []
    errors: list[str] = []
    seg_length = length / segments
    for i in range(segments):
        name = f"{base_name}_{i}"
        if direction.lower() == "x":
            x = start_x + i * seg_length + seg_length / 2
            z = start_z
        else:
            x = start_x
            z = start_z + i * seg_length + seg_length / 2
        y = start_y + height / 2
        try:
            res = _create_primitive("Cube", name, x, y, z)
            _set_scale(name, seg_length if direction.lower() == "x" else thickness, height, seg_length if direction.lower() == "z" else thickness)
            created.append({"name": name, "result": res})
        except Exception as e:
            errors.append(f"{name}: {e}")
    return {"ok": len(errors) == 0, "created_count": len(created), "errors": errors, "objects": [o["name"] for o in created]}


@tool(description="Create a simple room: floor, 4 walls, optional ceiling, light and camera.")
def unity_create_room(
    width: float = 10.0,
    depth: float = 10.0,
    height: float = 3.0,
    wall_thickness: float = 0.2,
    with_ceiling: bool = False,
    base_name: str = "Room",
    center_x: float = 0.0,
    center_y: float = 0.0,
    center_z: float = 0.0,
) -> dict:
    if _UNITY is None:
        return {"ok": False, "error": "UnityBridge is not initialized"}
    created: list[str] = []
    errors: list[str] = []

    # Floor
    floor_name = f"{base_name}_Floor"
    try:
        _create_primitive("Cube", floor_name, center_x, center_y - wall_thickness / 2, center_z)
        _set_scale(floor_name, width, wall_thickness, depth)
        created.append(floor_name)
    except Exception as e:
        errors.append(f"floor: {e}")

    # Walls
    walls = [
        ("Wall_Front", center_x, center_y + height / 2, center_z - depth / 2 + wall_thickness / 2, width, height, wall_thickness),
        ("Wall_Back", center_x, center_y + height / 2, center_z + depth / 2 - wall_thickness / 2, width, height, wall_thickness),
        ("Wall_Left", center_x - width / 2 + wall_thickness / 2, center_y + height / 2, center_z, wall_thickness, height, depth),
        ("Wall_Right", center_x + width / 2 - wall_thickness / 2, center_y + height / 2, center_z, wall_thickness, height, depth),
    ]
    for wname, wx, wy, wz, sx, sy, sz in walls:
        try:
            _create_primitive("Cube", f"{base_name}_{wname}", wx, wy, wz)
            _set_scale(f"{base_name}_{wname}", sx, sy, sz)
            created.append(f"{base_name}_{wname}")
        except Exception as e:
            errors.append(f"{wname}: {e}")

    # Ceiling
    if with_ceiling:
        ceil_name = f"{base_name}_Ceiling"
        try:
            _create_primitive("Cube", ceil_name, center_x, center_y + height + wall_thickness / 2, center_z)
            _set_scale(ceil_name, width, wall_thickness, depth)
            created.append(ceil_name)
        except Exception as e:
            errors.append(f"ceiling: {e}")

    # Light
    light_name = f"{base_name}_Light"
    try:
        _UNITY.call(
            "create_light",
            {
                "name": light_name,
                "light_type": "Point",
                "position": {"x": center_x, "y": center_y + height - 0.5, "z": center_z},
                "color": {"r": 1, "g": 1, "b": 1, "a": 1},
                "intensity": 1.5,
                "range": max(width, depth) * 1.5,
            },
        )
        created.append(light_name)
    except Exception as e:
        errors.append(f"light: {e}")

    # Camera
    cam_name = f"{base_name}_Camera"
    try:
        _UNITY.call(
            "create_empty",
            {
                "name": cam_name,
                "position": {"x": center_x, "y": center_y + height * 0.8, "z": center_z - depth * 0.4},
            },
        )
        _UNITY.call("add_component", {"name": cam_name, "type": "Camera"})
        _UNITY.call("set_camera", {"name": cam_name, "fov": 60})
        created.append(cam_name)
    except Exception as e:
        errors.append(f"camera: {e}")

    return {"ok": len(errors) == 0, "created_count": len(created), "errors": errors, "objects": created}
