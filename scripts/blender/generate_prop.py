"""Procedural prop generator for the studio AI asset pipeline.

The "AI learning layer": Claude reads the Briar Hollow DOCS
(level-instance-links.md, art-bible-briar-hollow.md) and manufactures
the environment props the vertical slice needs, in 3D, via Blender —
within the DOCS' AI usage line (environment / concept / blockout, NOT
final hero or boss meshes).

Usage:
    blender --background --python scripts/blender/generate_prop.py -- \
        --type shrine --output /path/final.fbx \
        [--seed 42] [--scale 1.0] [--preview /path/preview.png]

Primitive set (kept for back-compat):
    rock crate pillar column

Briar Hollow environment set (DOCS-driven, art-bible aligned —
"natural beauty corrupted by patient violence"):
    boulder    - large mossy boulder, flat base
    stump      - broken tree stump with root flares          (M_Bark)
    deadtrunk  - tall snapped leaning trunk                   (M_Bark)
    totem      - RestTotem: stacked carved stone discs        (M_Stone)
    shrine     - SoulShrine_OldRoots: altar + root arch ring  (M_Stone/M_Bark)
    gate       - BossGate_RootVeil: leaning posts + root lintel
    bench      - CraftingBench (Camp tier1)                   (M_Wood)
    banner     - WarBanner: pole + hanging cloth              (M_Wood/M_Cloth)
    rack       - WeaponRack A-frame                           (M_Wood)

Every build is deterministic per seed, low-poly, base at z=0 (sits on
terrain), single joined mesh with the DOCS material-slot contract so it
imports clean (never white) into Unity.
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

PRIMITIVE_TYPES = ("rock", "crate", "pillar", "column")
WORLD_TYPES = ("boulder", "stump", "deadtrunk", "totem", "shrine",
               "gate", "bench", "banner", "rack")
# Low-poly trees (HDRP-cheap: 1 mesh, 2 mats, ~200-400 tris) — built
# to replace the heavy PolyHaven GLB forest that tanked HDRP.
TREE_TYPES = ("pine", "fir", "deadpine", "shrub")
SUPPORTED_TYPES = PRIMITIVE_TYPES + WORLD_TYPES + TREE_TYPES

# Art-bible palette (linear-ish sRGB): wet dark earth brown, sickly
# moss green, burnt ash grey, dry-blood red, cold stone.
_MATS = {
    "M_Stone":  ((0.30, 0.30, 0.31, 1.0), 0.82),
    "M_Bark":   ((0.16, 0.11, 0.07, 1.0), 0.78),
    "M_Wood":   ((0.27, 0.18, 0.10, 1.0), 0.66),
    "M_Cloth":  ((0.34, 0.07, 0.07, 1.0), 0.85),
    "M_Ash":    ((0.13, 0.13, 0.14, 1.0), 0.74),
    "M_Moss":   ((0.20, 0.27, 0.13, 1.0), 0.80),
    "M_Needle": ((0.10, 0.20, 0.12, 1.0), 0.86),  # dark sickly pine
    "M_NeedleDry": ((0.20, 0.19, 0.12, 1.0), 0.88),
}


def parse_args() -> dict | None:
    try:
        sep = sys.argv.index("--")
        argv = sys.argv[sep + 1:]
    except ValueError:
        print("ERROR: pass arguments after '--' separator")
        return None
    out: dict = {"type": None, "output": None, "seed": 0, "scale": 1.0,
                 "preview": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--type" and i + 1 < len(argv):
            out["type"] = argv[i + 1]; i += 2
        elif a == "--output" and i + 1 < len(argv):
            out["output"] = argv[i + 1]; i += 2
        elif a == "--seed" and i + 1 < len(argv):
            out["seed"] = int(argv[i + 1]); i += 2
        elif a == "--scale" and i + 1 < len(argv):
            out["scale"] = float(argv[i + 1]); i += 2
        elif a == "--preview" and i + 1 < len(argv):
            out["preview"] = argv[i + 1]; i += 2
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
    for block in (bpy.data.meshes, bpy.data.materials):
        for b in list(block):
            if b.users == 0:
                block.remove(b)


def _mat(name: str) -> bpy.types.Material:
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    color, rough = _MATS.get(name, ((0.5, 0.5, 0.5, 1.0), 0.7))
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = color
    return m


def _assign(obj: bpy.types.Object, mat_name: str) -> bpy.types.Object:
    obj.data.materials.clear()
    obj.data.materials.append(_mat(mat_name))
    return obj


def _jitter_verts(obj, rng, amp, axis_bias=(1.0, 1.0, 1.0)) -> None:
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    for v in bm.verts:
        v.co.x += (rng.random() - 0.5) * amp * axis_bias[0]
        v.co.y += (rng.random() - 0.5) * amp * axis_bias[1]
        v.co.z += (rng.random() - 0.5) * amp * axis_bias[2]
    bm.to_mesh(me)
    bm.free()


def _join(objs: list, name: str) -> bpy.types.Object:
    objs = [o for o in objs if o is not None]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    j = bpy.context.active_object
    j.name = name
    # Drop pivot to the base so it sits on the terrain surface.
    me = j.data
    min_z = min((j.matrix_world @ v.co).z for v in me.vertices)
    for v in me.vertices:
        v.co.z -= min_z
    j.location = (0.0, 0.0, 0.0)
    return j


def _cyl(r, d, loc, verts=12, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d,
                                        location=loc)
    o = bpy.context.active_object
    o.rotation_euler = rot
    return o


def _cube(size, loc, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_cube_add(size=size, location=loc)
    o = bpy.context.active_object
    o.scale = scale
    return o


def _ico(r, loc, subd=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subd, radius=r,
                                          location=loc)
    return bpy.context.active_object


def _cone(r1, r2, d, loc, verts=7):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1,
                                    radius2=r2, depth=d, location=loc)
    return bpy.context.active_object


# ─── low-poly trees (HDRP-cheap) ──────────────────────────────────────
# One joined mesh, 2 material slots, ~200-400 tris. Designed to replace
# the heavy multi-hundred-renderer PolyHaven GLB trees that tanked HDRP.
def _conifer(seed, s, *, tiers, trunk_r, total_h, spread, dry=False):
    rng = random.Random(seed)
    th = total_h * s
    tr = trunk_r * s
    trunk = _cone(tr, tr * 0.6, th * (0.95 if dry else 0.62),
                  (0, 0, th * (0.47 if dry else 0.31)), 6)
    _assign(trunk, "M_Bark")
    parts = [trunk]
    if not dry:
        nmat = "M_NeedleDry" if rng.random() < 0.18 else "M_Needle"
        base_z = th * 0.30
        seg = (th * 0.72) / tiers
        rad = spread * s
        for k in range(tiers):
            z = base_z + k * seg * 0.82
            r = rad * (1.0 - k / (tiers + 0.5))
            cone = _cone(max(0.05 * s, r), 0.0, seg * 1.7,
                         (0, 0, z + seg * 0.7), 7)
            cone.scale = (1.0, 1.0, 1.0)
            _assign(cone, nmat)
            parts.append(cone)
    else:
        # dead pine: bare slanted branch stubs
        for k in range(5):
            ang = rng.random() * math.tau
            zb = th * (0.45 + 0.1 * k)
            br = _cone(0.05 * s, 0.0, th * 0.28,
                       (math.cos(ang) * 0.12 * s, math.sin(ang) * 0.12 * s,
                        zb), 4)
            br.rotation_euler = (1.1, 0, ang)
            _assign(br, "M_Bark")
            parts.append(br)
    j = _join(parts, "Tree")
    # tiny per-instance variation so a scattered forest isn't a clone army
    j.rotation_euler = (rng.uniform(-0.04, 0.04), rng.uniform(-0.04, 0.04),
                        rng.uniform(0, 6.28))
    # NOTE: do NOT _assign() here — _join keeps the per-part material
    # slots (M_Bark trunk + M_Needle foliage). Flattening would make
    # the whole tree one colour (the bug that made foliage bark-brown).
    return j


def _build_pine(seed, s):
    return _conifer(seed, s, tiers=4, trunk_r=0.10, total_h=4.2,
                    spread=0.95)


def _build_fir(seed, s):
    return _conifer(seed, s, tiers=5, trunk_r=0.12, total_h=3.4,
                    spread=1.25)


def _build_deadpine(seed, s):
    return _conifer(seed, s, tiers=0, trunk_r=0.11, total_h=3.6,
                    spread=0.4, dry=True)


def _build_shrub(seed, s):
    rng = random.Random(seed)
    parts = []
    for k in range(3):
        b = _ico(rng.uniform(0.35, 0.6) * s,
                 (rng.uniform(-0.3, 0.3) * s, rng.uniform(-0.3, 0.3) * s,
                  rng.uniform(0.3, 0.55) * s), 1)
        _jitter_verts(b, rng, 0.12 * s)
        _assign(b, "M_Needle")
        parts.append(b)
    return _assign(_join(parts, "Shrub"), "M_Needle")


# ─── primitive set (back-compat) ──────────────────────────────────────
def _build_rock(seed, s):
    o = _ico(0.5 * s, (0, 0, 0))
    _jitter_verts(o, random.Random(seed), 0.25 * s, (1.0, 0.7, 1.1))
    return _assign(_join([o], "Rock"), "M_Stone")


def _build_crate(seed, s):
    o = _cube(1.0 * s, (0, 0, 0))
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.bevel(offset=0.03 * s, segments=2)
    bpy.ops.object.mode_set(mode="OBJECT")
    return _assign(_join([o], "Crate"), "M_Wood")


def _build_pillar(seed, s):
    return _assign(_join([_cyl(0.3 * s, 2.0 * s, (0, 0, 0))], "Pillar"),
                   "M_Stone")


def _build_column(seed, s):
    shaft = _cyl(0.3 * s, 2.0 * s, (0, 0, 0), 16)
    base = _cyl(0.45 * s, 0.15 * s, (0, 0, -1.0 * s - 0.075 * s), 16)
    cap = _cyl(0.45 * s, 0.15 * s, (0, 0, 1.0 * s + 0.075 * s), 16)
    return _assign(_join([shaft, base, cap], "Column"), "M_Stone")


# ─── Briar Hollow environment set ─────────────────────────────────────
def _build_boulder(seed, s):
    rng = random.Random(seed)
    o = _ico(0.9 * s, (0, 0, 0), subd=2)
    _jitter_verts(o, rng, 0.42 * s, (1.0, 1.0, 0.65))
    # flatten the bottom so it reads as resting, not floating
    for v in o.data.vertices:
        if v.co.z < -0.35 * s:
            v.co.z = -0.35 * s
    return _assign(_join([o], "Boulder"), "M_Stone")


def _build_stump(seed, s):
    rng = random.Random(seed)
    trunk = _cyl(0.34 * s, 0.85 * s, (0, 0, 0), 14)
    # jagged snapped top
    bm = bmesh.new(); bm.from_mesh(trunk.data)
    for v in bm.verts:
        if v.co.z > 0.30 * s:
            v.co.z += (rng.random()) * 0.32 * s
    bm.to_mesh(trunk.data); bm.free()
    roots = []
    for k in range(4):
        ang = k * (math.pi / 2) + rng.random() * 0.5
        rt = _cyl(0.12 * s, 0.6 * s,
                  (math.cos(ang) * 0.34 * s, math.sin(ang) * 0.34 * s,
                   -0.32 * s),
                  8, (rng.random() * 0.4 + 1.0, 0, ang))
        roots.append(_assign(rt, "M_Bark"))
    return _assign(_join([trunk] + roots, "Stump"), "M_Bark")


def _build_deadtrunk(seed, s):
    rng = random.Random(seed)
    segs = []
    z = 0.0
    lean = rng.random() * 0.18
    for k in range(4):
        r = (0.30 - k * 0.05) * s
        d = (1.1 - k * 0.12) * s
        seg = _cyl(max(0.06 * s, r), d, (lean * k * s, 0, z + d / 2), 12,
                   (0, lean, 0))
        segs.append(seg)
        z += d * 0.92
    # snapped jagged top on the last segment
    bm = bmesh.new(); bm.from_mesh(segs[-1].data)
    for v in bm.verts:
        if v.co.z > 0:
            v.co.z += rng.random() * 0.45 * s
    bm.to_mesh(segs[-1].data); bm.free()
    return _assign(_join(segs, "DeadTrunk"), "M_Bark")


def _build_totem(seed, s):
    rng = random.Random(seed)
    parts = []
    z = 0.0
    for k in range(4):
        r = (0.42 - k * 0.06) * s + rng.random() * 0.03 * s
        d = (0.34 + rng.random() * 0.1) * s
        disc = _cyl(r, d, (0, 0, z + d / 2), 10)
        _jitter_verts(disc, rng, 0.05 * s, (1, 1, 0.2))
        parts.append(disc)
        z += d
    # carved notch cap
    cap = _cube(0.5 * s, (0, 0, z + 0.18 * s), (0.5, 0.5, 0.35))
    parts.append(cap)
    return _assign(_join(parts, "RestTotem"), "M_Stone")


def _build_shrine(seed, s):
    # SoulShrine_OldRoots: a low offering altar wrapped by a veil of
    # old roots leaning STRONGLY inward to a canopy over the stone
    # (art bible: "natural beauty corrupted by patient violence").
    rng = random.Random(seed)
    parts = []
    base = _cyl(1.55 * s, 0.22 * s, (0, 0, 0.11 * s), 14)
    _jitter_verts(base, rng, 0.05 * s, (1, 1, 0.3))
    parts.append(_assign(base, "M_Stone"))
    altar = _cube(1.0 * s, (0, 0, 0.44 * s), (0.85, 0.85, 0.7))
    parts.append(_assign(altar, "M_Stone"))
    n = 6
    for k in range(n):
        ang = (k / n) * math.tau + rng.random() * 0.15
        # root climbs from the outer ring up and inward over the altar
        cx, cy = math.cos(ang) * 0.95 * s, math.sin(ang) * 0.95 * s
        arc = _cyl(0.11 * s, 2.5 * s, (cx, cy, 1.05 * s), 7,
                   (math.sin(ang) * 0.95,   # tilt toward centre
                    -math.cos(ang) * 0.95,
                    ang + rng.random() * 0.2))
        parts.append(_assign(arc, "M_Bark"))
    # converging crown knot where the roots meet over the altar
    knot = _ico(0.26 * s, (0, 0, 2.15 * s), 1)
    _jitter_verts(knot, rng, 0.10 * s)
    parts.append(_assign(knot, "M_Bark"))
    return _assign(_join(parts, "SoulShrine"), "M_Stone")


def _build_gate(seed, s):
    # BossGate_RootVeil: two heavy stone posts leaning toward each
    # other, a thick sagging root lintel, and hanging root strands
    # (the "veil") you pass through to reach the boss arena.
    rng = random.Random(seed)
    lp = _cyl(0.34 * s, 3.6 * s, (-1.55 * s, 0, 1.8 * s), 8, (0, 0.16, 0))
    rp = _cyl(0.34 * s, 3.6 * s, (1.55 * s, 0, 1.8 * s), 8, (0, -0.16, 0))
    _jitter_verts(lp, rng, 0.07 * s); _jitter_verts(rp, rng, 0.07 * s)
    parts = [_assign(lp, "M_Stone"), _assign(rp, "M_Stone")]
    # sagging root lintel across the top
    lintel = _cyl(0.18 * s, 3.5 * s, (0, 0, 3.45 * s), 8,
                  (0, math.pi / 2, 0))
    bm = bmesh.new(); bm.from_mesh(lintel.data)
    for v in bm.verts:
        v.co.z -= 0.28 * s * (1.0 - (abs(v.co.x) / (1.75 * s)))
    bm.to_mesh(lintel.data); bm.free()
    parts.append(_assign(lintel, "M_Bark"))
    # hanging root-veil strands of varying length
    for k in range(5):
        fx = (-1.3 + k * 0.65) * s
        ln = (0.9 + rng.random() * 1.1) * s
        strand = _cyl(0.05 * s, ln, (fx, 0, 3.25 * s - ln / 2), 6,
                      (rng.random() * 0.18 - 0.09, 0, 0))
        parts.append(_assign(strand, "M_Bark"))
    return _assign(_join(parts, "BossGate"), "M_Stone")


def _build_bench(seed, s):
    top = _cube(1.0 * s, (0, 0, 0.62 * s), (1.3, 0.6, 0.1))
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            legs.append(_cube(1.0 * s,
                              (sx * 0.55 * s, sy * 0.22 * s, 0.31 * s),
                              (0.1, 0.1, 0.62)))
    back = _cube(1.0 * s, (0, -0.28 * s, 0.95 * s), (1.3, 0.08, 0.35))
    return _assign(_join([top] + legs + [back], "CraftingBench"), "M_Wood")


def _build_banner(seed, s):
    pole = _cyl(0.07 * s, 3.2 * s, (0, 0, 1.6 * s), 8)
    cross = _cyl(0.05 * s, 1.2 * s, (0, 0, 2.9 * s), 6, (math.pi / 2, 0, 0))
    cloth = _cube(1.0 * s, (0, 0.02 * s, 2.1 * s), (0.55, 0.02, 0.85))
    rng = random.Random(seed)
    bm = bmesh.new(); bm.from_mesh(cloth.data)
    for v in bm.verts:
        v.co.x += math.sin(v.co.z * 6.0 + rng.random()) * 0.05 * s
    bm.to_mesh(cloth.data); bm.free()
    return _assign(_join([_assign(pole, "M_Wood"), _assign(cross, "M_Wood"),
                          _assign(cloth, "M_Cloth")], "WarBanner"),
                   "M_Wood")


def _build_rack(seed, s):
    parts = []
    for side in (-1, 1):
        a = _cyl(0.06 * s, 1.7 * s, (side * 0.5 * s, -0.3 * s, 0.8 * s),
                 6, (0.32, 0, 0))
        b = _cyl(0.06 * s, 1.7 * s, (side * 0.5 * s, 0.3 * s, 0.8 * s),
                 6, (-0.32, 0, 0))
        parts += [a, b]
    topbar = _cyl(0.05 * s, 1.3 * s, (0, 0, 1.45 * s), 6,
                  (0, math.pi / 2, 0))
    rail = _cyl(0.05 * s, 1.3 * s, (0, 0, 0.55 * s), 6,
                (0, math.pi / 2, 0))
    parts += [topbar, rail]
    return _assign(_join(parts, "WeaponRack"), "M_Wood")


_BUILDERS = {
    "rock": _build_rock, "crate": _build_crate, "pillar": _build_pillar,
    "column": _build_column, "boulder": _build_boulder,
    "stump": _build_stump, "deadtrunk": _build_deadtrunk,
    "totem": _build_totem, "shrine": _build_shrine, "gate": _build_gate,
    "bench": _build_bench, "banner": _build_banner, "rack": _build_rack,
    "pine": _build_pine, "fir": _build_fir, "deadpine": _build_deadpine,
    "shrub": _build_shrub,
}


def build(prop_type: str, seed: int, scale: float) -> bpy.types.Object:
    fn = _BUILDERS.get(prop_type)
    if fn is None:
        raise ValueError(f"Unknown prop type: {prop_type}")
    obj = fn(seed, scale)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True,
                                   scale=True)
    return obj


def render_preview(obj, preview_path: str) -> None:
    try:
        scn = bpy.context.scene
        scn.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        try:
            bpy.context.scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            pass
    scn = bpy.context.scene
    scn.render.resolution_x = 512
    scn.render.resolution_y = 512
    scn.render.filepath = preview_path
    # frame the prop
    bbox = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
    cz = sum(v.z for v in bbox) / 8.0
    rad = max((v - Vector((0, 0, cz))).length for v in bbox) or 1.0
    bpy.ops.object.camera_add(location=(rad * 2.4, -rad * 2.4,
                                        cz + rad * 1.4))
    cam = bpy.context.active_object
    cam.rotation_euler = (math.radians(62), 0, math.radians(45))
    scn.camera = cam
    bpy.ops.object.light_add(type="SUN",
                             location=(rad * 2, -rad * 2, rad * 4))
    bpy.context.active_object.data.energy = 4.0
    try:
        bpy.ops.render.render(write_still=True)
        print(f"PREVIEW_RENDERED: {preview_path}")
    except Exception as exc:
        print(f"WARN: preview render failed: {exc}")


def export_fbx(obj, output_path: str) -> None:
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
        mesh_smooth_type="FACE",
        use_tspace=True,
        bake_anim=False,
        use_mesh_modifiers=True,
        axis_forward="-Z",
        axis_up="Y",
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
    if args.get("preview"):
        try:
            render_preview(obj, args["preview"])
        except Exception as exc:
            print(f"WARN: preview failed: {exc}")
        # re-select the prop for export
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
    try:
        export_fbx(obj, args["output"])
    except Exception as exc:
        print(f"ERROR: export failed: {exc}")
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
