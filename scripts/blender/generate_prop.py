"""Procedural prop generator for the studio asset pipeline.

Usage:
    blender --background --python scripts/blender/generate_prop.py -- \
        --type rock --output /path/to/output.fbx \
        [--seed 42] [--scale 1.0]

Supported types (parametric, deterministic per seed):
    rock     - randomly-deformed icosphere, low poly
    crate    - beveled cube
    pillar   - tall cylinder with end caps
    column   - cylinder with a wider capital + base

The script clears the default scene, builds one prop at the origin,
exports to FBX, and exits. Designed for the studio's
studio_generate_prop_asset tool.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import bpy
import bmesh


SUPPORTED_TYPES = ("rock", "crate", "pillar", "column")


def parse_args() -> dict | None:
    try:
        sep = sys.argv.index("--")
        argv = sys.argv[sep + 1 :]
    except ValueError:
        print("ERROR: pass arguments after '--' separator")
        return None

    out: dict = {"type": None, "output": None, "seed": 0, "scale": 1.0}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--type" and i + 1 < len(argv):
            out["type"] = argv[i + 1]
            i += 2
        elif a == "--output" and i + 1 < len(argv):
            out["output"] = argv[i + 1]
            i += 2
        elif a == "--seed" and i + 1 < len(argv):
            out["seed"] = int(argv[i + 1])
            i += 2
        elif a == "--scale" and i + 1 < len(argv):
            out["scale"] = float(argv[i + 1])
            i += 2
        else:
            i += 1
    if not out["type"] or not out["output"]:
        print("ERROR: --type and --output are required")
        return None
    if out["type"] not in SUPPORTED_TYPES:
        print(f"ERROR: --type must be one of {SUPPORTED_TYPES}")
        return None
    return out


def _clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def _build_rock(seed: int, scale: float) -> bpy.types.Object:
    rng = random.Random(seed)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.5 * scale)
    obj = bpy.context.active_object
    obj.name = "Rock"
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # Per-vertex random displacement -- low-poly weathered look
    for v in bm.verts:
        jitter = (rng.random() - 0.5) * 0.25 * scale
        v.co.x += jitter
        v.co.y += jitter * 0.7
        v.co.z += jitter * 1.1
    bm.to_mesh(mesh)
    bm.free()
    return obj


def _build_crate(seed: int, scale: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1.0 * scale)
    obj = bpy.context.active_object
    obj.name = "Crate"
    # Bevel the edges for a slightly weathered crate look
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bevel(offset=0.03 * scale, segments=2)
    bpy.ops.object.mode_set(mode="OBJECT")
    return obj


def _build_pillar(seed: int, scale: float) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=12,
        radius=0.3 * scale,
        depth=2.0 * scale,
    )
    obj = bpy.context.active_object
    obj.name = "Pillar"
    return obj


def _build_column(seed: int, scale: float) -> bpy.types.Object:
    """Pillar shaft + wider capital + base, all under a single mesh."""
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, radius=0.3 * scale, depth=2.0 * scale, location=(0, 0, 0)
    )
    shaft = bpy.context.active_object
    shaft.name = "Column"

    # Base
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, radius=0.45 * scale, depth=0.15 * scale,
        location=(0, 0, -1.0 * scale - 0.075 * scale),
    )
    base = bpy.context.active_object

    # Capital
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=16, radius=0.45 * scale, depth=0.15 * scale,
        location=(0, 0, 1.0 * scale + 0.075 * scale),
    )
    capital = bpy.context.active_object

    # Join shaft + base + capital
    bpy.ops.object.select_all(action="DESELECT")
    shaft.select_set(True)
    base.select_set(True)
    capital.select_set(True)
    bpy.context.view_layer.objects.active = shaft
    bpy.ops.object.join()
    return bpy.context.active_object


def build(prop_type: str, seed: int, scale: float) -> bpy.types.Object:
    if prop_type == "rock":
        return _build_rock(seed, scale)
    if prop_type == "crate":
        return _build_crate(seed, scale)
    if prop_type == "pillar":
        return _build_pillar(seed, scale)
    if prop_type == "column":
        return _build_column(seed, scale)
    raise ValueError(f"Unknown prop type: {prop_type}")


def export_fbx(obj: bpy.types.Object, output_path: str) -> None:
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=str(out_path),
        use_selection=True,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE",
        bake_space_transform=False,
        object_types={"MESH"},
        bake_anim=False,
        use_mesh_modifiers=True,
    )
    print(f"PROP_GENERATED: {out_path}")


def main() -> int:
    args = parse_args()
    if args is None:
        return 2
    _clear_scene()
    try:
        obj = build(args["type"], args["seed"], args["scale"])
    except Exception as exc:
        print(f"ERROR: build failed: {exc}")
        return 3
    try:
        export_fbx(obj, args["output"])
    except Exception as exc:
        print(f"ERROR: export failed: {exc}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
