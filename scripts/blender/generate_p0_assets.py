# Thorny Ivy - P0 asset üreticisi (headless Blender)
#
# Kullanım:
#   blender --background --factory-startup --python generate_p0_assets.py -- \
#       --out "C:/dev/UnityProje/Assets/FantasyRPG" \
#       --blend "C:/dev/UnityProje/BlenderAssets/p0_assets.blend"
#
# SceneBuilder.cs'in `Assets/FantasyRPG` altında isimle aradığı GLB'leri üretir:
#   PineTree, FirTree, IslandTree, DeadTreeTrunk, TreeStump1, TreeStump2,
#   StoneFire, Boulder1, Rock9, Barrel1, WoodenCrate1, Lantern
#
# Stil: koyu gotik, stilize low-poly (faceted). Ağaç materyalleri
# IslandTreePainter'ın aradığı "foliage"/"bark" anahtar kelimelerini içerir.
# Üretim deterministiktir (sabit seed) - aynı script aynı asset'i üretir.

import argparse
import math
import os
import random
import sys

import bpy

SEED = 41


# --------------------------------------------------------------------- temel
def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, help="GLB çıkış klasörü")
    p.add_argument("--blend", default="", help="Galeri .blend kayıt yolu (opsiyonel)")
    return p.parse_args(argv)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block_list in (bpy.data.meshes, bpy.data.materials):
        for block in list(block_list):
            if block.users == 0:
                block_list.remove(block)


_MATS = {}


def mat(name, rgba, rough=0.85, metallic=0.0, emission=None, emission_strength=4.0):
    if name in _MATS:
        return _MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metallic
    if emission is not None:
        # 4.x: "Emission Color"; eski sürümler: "Emission"
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = emission
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    _MATS[name] = m
    return m


def _finish(obj, material):
    obj.data.materials.append(material)
    return obj


def cone(r_bottom, r_top, depth, loc, material, verts=10, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(
        vertices=verts, radius1=r_bottom, radius2=r_top, depth=depth,
        location=loc, rotation=rot,
    )
    return _finish(bpy.context.active_object, material)


def cylinder(radius, depth, loc, material, verts=10, rot=(0, 0, 0)):
    return cone(radius, radius, depth, loc, material, verts=verts, rot=rot)


def icosphere(radius, loc, material, subdiv=1, noise=0.0, seed=0, squash=1.0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius, location=loc)
    obj = bpy.context.active_object
    if noise > 0:
        rng = random.Random(seed)
        for v in obj.data.vertices:
            v.co *= 1.0 + rng.uniform(-noise, noise)
    if squash != 1.0:
        obj.scale[2] = squash
        bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, material)


def box(dx, dy, dz, loc, material, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc, rotation=rot)
    obj = bpy.context.active_object
    obj.scale = (dx / 2, dy / 2, dz / 2)
    bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, material)


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    return obj


# ------------------------------------------------------------------- paletler
def pal():
    return {
        "pine_bark":   mat("PineBark_bark",       (0.13, 0.09, 0.06, 1), rough=0.95),
        "pine_leaf":   mat("PineFoliage_foliage", (0.05, 0.11, 0.07, 1), rough=0.9),
        "fir_leaf":    mat("FirFoliage_foliage",  (0.04, 0.09, 0.06, 1), rough=0.9),
        "broad_bark":  mat("IslandBark_bark",     (0.16, 0.11, 0.07, 1), rough=0.95),
        "broad_leaf":  mat("IslandFoliage_foliage", (0.07, 0.13, 0.05, 1), rough=0.9),
        "dead_bark":   mat("DeadBark_bark",       (0.18, 0.15, 0.12, 1), rough=1.0),
        "rock":        mat("Rock_stone",          (0.30, 0.30, 0.31, 1), rough=0.95),
        "wood":        mat("Prop_wood",           (0.22, 0.15, 0.09, 1), rough=0.9),
        "iron":        mat("Prop_iron",           (0.15, 0.15, 0.17, 1), rough=0.5, metallic=0.9),
        "ember":       mat("Fire_ember",          (0.6, 0.15, 0.02, 1), rough=0.6,
                           emission=(1.0, 0.35, 0.05, 1), emission_strength=6.0),
        "glow":        mat("Lantern_glow",        (1.0, 0.75, 0.3, 1), rough=0.4,
                           emission=(1.0, 0.7, 0.25, 1), emission_strength=5.0),
    }


# ------------------------------------------------------------------- asset'ler
def build_pine_tree(p):
    parts = [cylinder(0.20, 1.8, (0, 0, 0.9), p["pine_bark"], verts=8)]
    z, r = 1.5, 1.5
    for i in range(4):
        h = 1.5 - i * 0.15
        parts.append(cone(r, 0.02, h, (0, 0, z + h / 2), p["pine_leaf"], verts=9))
        z += h * 0.62
        r *= 0.72
    return join(parts, "PineTree")


def build_fir_tree(p):
    parts = [cylinder(0.16, 2.2, (0, 0, 1.1), p["pine_bark"], verts=8)]
    z, r = 1.2, 1.15
    for i in range(6):
        h = 1.2 - i * 0.08
        parts.append(cone(r, 0.02, h, (0, 0, z + h / 2), p["fir_leaf"], verts=9))
        z += h * 0.55
        r *= 0.78
    return join(parts, "FirTree")


def build_island_tree(p):
    rng = random.Random(SEED)
    parts = [cone(0.34, 0.22, 2.6, (0, 0, 1.3), p["broad_bark"], verts=9)]
    for i in range(5):
        ang = i * (2 * math.pi / 5)
        d = 0.55 if i else 0.0
        parts.append(icosphere(
            1.05 + rng.uniform(-0.15, 0.2),
            (math.cos(ang) * d, math.sin(ang) * d, 3.1 + rng.uniform(-0.2, 0.35)),
            p["broad_leaf"], subdiv=1, noise=0.12, seed=SEED + i,
        ))
    return join(parts, "IslandTree")


def build_dead_tree_trunk(p):
    parts = [cone(0.26, 0.08, 3.4, (0, 0, 1.7), p["dead_bark"], verts=8)]
    parts.append(cylinder(0.06, 1.1, (0.35, 0, 2.2), p["dead_bark"], verts=6,
                          rot=(0, math.radians(55), 0)))
    parts.append(cylinder(0.05, 0.9, (-0.3, 0.1, 2.7), p["dead_bark"], verts=6,
                          rot=(math.radians(-20), math.radians(-50), 0)))
    return join(parts, "DeadTreeTrunk")


def build_stump(p, name, radius, height):
    parts = [cone(radius, radius * 0.9, height, (0, 0, height / 2), p["dead_bark"], verts=9)]
    return join(parts, name)


def build_stone_fire(p):
    rng = random.Random(SEED)
    parts = []
    for i in range(8):
        ang = i * (2 * math.pi / 8) + rng.uniform(-0.15, 0.15)
        parts.append(icosphere(
            0.20 + rng.uniform(-0.04, 0.05),
            (math.cos(ang) * 0.75, math.sin(ang) * 0.75, 0.12),
            p["rock"], subdiv=1, noise=0.2, seed=SEED + 10 + i, squash=0.7,
        ))
    for i in range(3):
        ang = i * (2 * math.pi / 3)
        parts.append(cylinder(
            0.08, 1.0,
            (math.cos(ang) * 0.18, math.sin(ang) * 0.18, 0.38), p["wood"], verts=7,
            rot=(math.radians(38) * math.cos(ang + math.pi / 2),
                 math.radians(38) * math.sin(ang + math.pi / 2), 0),
        ))
    parts.append(cylinder(0.42, 0.07, (0, 0, 0.05), p["ember"], verts=12))
    return join(parts, "StoneFire")


def build_boulder(p, name, radius, noise, seed, squash):
    return join([icosphere(radius, (0, 0, radius * squash * 0.8), p["rock"],
                           subdiv=2, noise=noise, seed=seed, squash=squash)], name)


def build_barrel(p):
    parts = [
        cylinder(0.34, 0.28, (0, 0, 0.14), p["wood"], verts=14),
        cylinder(0.40, 0.36, (0, 0, 0.46), p["wood"], verts=14),
        cylinder(0.34, 0.26, (0, 0, 0.77), p["wood"], verts=14),
        cylinder(0.41, 0.05, (0, 0, 0.24), p["iron"], verts=14),
        cylinder(0.41, 0.05, (0, 0, 0.68), p["iron"], verts=14),
    ]
    return join(parts, "Barrel1")


def build_crate(p):
    parts = [box(0.8, 0.8, 0.8, (0, 0, 0.4), p["wood"])]
    for z in (0.06, 0.74):
        parts.append(box(0.86, 0.86, 0.1, (0, 0, z), p["wood"]))
    parts.append(box(0.1, 0.84, 0.84, (0.39, 0, 0.4), p["wood"]))
    parts.append(box(0.84, 0.1, 0.84, (0, 0.39, 0.4), p["wood"]))
    return join(parts, "WoodenCrate1")


def build_lantern(p):
    parts = [
        box(0.22, 0.22, 0.04, (0, 0, 0.02), p["iron"]),
        box(0.16, 0.16, 0.22, (0, 0, 0.17), p["glow"]),
        box(0.03, 0.03, 0.24, (0.095, 0.095, 0.16), p["iron"]),
        box(0.03, 0.03, 0.24, (-0.095, 0.095, 0.16), p["iron"]),
        box(0.03, 0.03, 0.24, (0.095, -0.095, 0.16), p["iron"]),
        box(0.03, 0.03, 0.24, (-0.095, -0.095, 0.16), p["iron"]),
        cone(0.17, 0.02, 0.12, (0, 0, 0.34), p["iron"], verts=8),
    ]
    return join(parts, "Lantern")


BUILDERS = [
    ("PineTree", build_pine_tree),
    ("FirTree", build_fir_tree),
    ("IslandTree", build_island_tree),
    ("DeadTreeTrunk", build_dead_tree_trunk),
    ("TreeStump1", lambda p: build_stump(p, "TreeStump1", 0.38, 0.5)),
    ("TreeStump2", lambda p: build_stump(p, "TreeStump2", 0.28, 0.75)),
    ("StoneFire", build_stone_fire),
    ("Boulder1", lambda p: build_boulder(p, "Boulder1", 0.95, 0.22, SEED + 30, 0.75)),
    ("Rock9", lambda p: build_boulder(p, "Rock9", 0.45, 0.3, SEED + 31, 0.8)),
    ("Barrel1", build_barrel),
    ("WoodenCrate1", build_crate),
    ("Lantern", build_lantern),
]


def export_scene_fbx(filepath):
    # FBX: Unity'nin paketsiz, dogal okudugu format (GLB icin glTFast gerekirdi).
    # SceneBuilder boyutlari targetMeters ile normalize ettigi icin olcek ayari kritik degil.
    bpy.ops.export_scene.fbx(filepath=filepath, use_selection=False, add_leaf_bones=False)


def main():
    args = parse_args()
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)

    # Geçiş A: her asset'i BOŞ sahnede kur ve tek başına FBX'e ver.
    # (Tüm-sahne exportu, sürümler arası en taşınabilir yol.)
    produced = []
    for name, builder in BUILDERS:
        clean_scene()
        _MATS.clear()
        builder(pal())
        fp = os.path.join(out_dir, name + ".fbx")
        export_scene_fbx(fp)
        produced.append(fp)
        print(f"[p0] uretildi: {fp}")

    # Geçiş B: inceleme icin tum asset'leri yan yana dizen galeri .blend'i.
    if args.blend:
        clean_scene()
        _MATS.clear()
        x = 0.0
        for name, builder in BUILDERS:
            obj = builder(pal())
            obj.location.x = x
            x += 4.0
        blend_path = os.path.abspath(args.blend)
        os.makedirs(os.path.dirname(blend_path), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        print(f"[p0] galeri kaydedildi: {blend_path}")

    print(f"[p0] TAMAM - {len(produced)} asset uretildi.")


if __name__ == "__main__":
    main()
