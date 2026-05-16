"""Decimate a film-grade PolyHaven tree GLB into a game-ready low-poly
FBX that keeps the REAL silhouette but is cheap enough for a forest.

Why: the project's PolyHaven trees are 4-27 MILLION tris each (film/
photogrammetry) — impossible to instance in real-time. This imports
one, joins it, crushes it with a Collapse decimate to a target tri
budget, flattens to 2 cheap materials (green canopy + brown bark by
luminance), and exports a clean FBX + preview.

Usage:
  blender --background --python scripts/blender/decimate_tree.py -- \
    --glb <in.glb> --output <out.fbx> [--target 2600] [--preview p.png]
"""
from __future__ import annotations
import math, sys
from pathlib import Path
import bpy


def parse():
    try:
        argv = sys.argv[sys.argv.index("--") + 1:]
    except ValueError:
        print("ERROR: need args after --"); return None
    o = {"glb": None, "output": None, "target": 2600, "preview": None}
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--glb", "--output", "--preview") and i + 1 < len(argv):
            o[a[2:]] = argv[i + 1]; i += 2
        elif a == "--target" and i + 1 < len(argv):
            o["target"] = int(argv[i + 1]); i += 2
        else:
            i += 1
    if not o["glb"] or not o["output"]:
        print("ERROR: --glb and --output required"); return None
    return o


def main() -> int:
    a = parse()
    if a is None:
        return 2
    src = a["glb"]
    ext = Path(src).suffix.lower()
    try:
        if ext == ".blend":
            # open the .blend directly (keeps its meshes/materials)
            bpy.ops.wm.open_mainfile(filepath=src)
        else:
            bpy.ops.object.select_all(action="SELECT")
            bpy.ops.object.delete(use_global=False)
            if ext in (".glb", ".gltf"):
                bpy.ops.import_scene.gltf(filepath=src)
            elif ext == ".obj":
                try:
                    bpy.ops.wm.obj_import(filepath=src)        # Blender 4+
                except Exception:
                    bpy.ops.import_scene.obj(filepath=src)     # legacy
            elif ext == ".fbx":
                bpy.ops.import_scene.fbx(filepath=src)
            else:
                print(f"ERROR: unsupported input ext {ext}")
                return 3
    except Exception as exc:
        print(f"ERROR: import failed ({ext}): {exc}")
        return 3

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if not meshes:
        print("ERROR: no meshes in input")
        return 3

    bpy.ops.object.select_all(action="DESELECT")
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = "LP_RealTree"

    src_tris = len(obj.data.polygons)
    ratio = max(0.0005, min(1.0, a["target"] / max(1, src_tris)))
    dec = obj.modifiers.new("dec", type="DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = ratio
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier="dec")
    out_tris = len(obj.data.polygons)

    # Flatten to 2 cheap materials by original-material luminance:
    # darker -> bark, greener/brighter -> canopy. Keeps a 2-tone look
    # without textures (cheap, never white).
    def mk(name, rgba, rough):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        if b:
            b.inputs["Base Color"].default_value = rgba
            if "Roughness" in b.inputs:
                b.inputs["Roughness"].default_value = rough
        m.diffuse_color = rgba
        return m

    bark = mk("M_RealBark", (0.16, 0.11, 0.07, 1.0), 0.8)
    canopy = mk("M_RealCanopy", (0.13, 0.24, 0.14, 1.0), 0.85)
    orig = list(obj.data.materials)
    obj.data.materials.clear()
    obj.data.materials.append(bark)    # slot 0
    obj.data.materials.append(canopy)  # slot 1

    def lum(mat):
        try:
            c = mat.diffuse_color
            return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
        except Exception:
            return 0.5
    remap = {}
    for idx, om in enumerate(orig):
        g = (om.diffuse_color[1] if om else 0.3)
        r = (om.diffuse_color[0] if om else 0.3)
        remap[idx] = 1 if (g >= r and lum(om) > 0.12) else 0
    for poly in obj.data.polygons:
        poly.material_index = remap.get(poly.material_index, 1)

    # base at z=0 so it sits on the terrain (pivot-at-base)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    mn = min(v.co.z for v in obj.data.vertices)
    for v in obj.data.vertices:
        v.co.z -= mn

    out = Path(a["output"])
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=str(out), use_selection=True, apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_NONE", bake_space_transform=False,
        object_types={"MESH"}, mesh_smooth_type="FACE", use_tspace=True,
        bake_anim=False, use_mesh_modifiers=True,
        axis_forward="-Z", axis_up="Y")
    print(f"DECIMATED src_tris={src_tris} -> out_tris={out_tris} "
          f"ratio={ratio:.5f} -> {out}")

    if a.get("preview"):
        try:
            scn = bpy.context.scene
            try: scn.render.engine = "BLENDER_EEVEE_NEXT"
            except Exception:
                try: scn.render.engine = "BLENDER_EEVEE"
                except Exception: pass
            scn.render.resolution_x = 512
            scn.render.resolution_y = 512
            scn.render.filepath = a["preview"]
            bb = [obj.matrix_world @ __import__("mathutils").Vector(c)
                  for c in obj.bound_box]
            cz = sum(p.z for p in bb) / 8.0
            rad = max((p - __import__("mathutils").Vector((0, 0, cz))).length
                      for p in bb) or 2.0
            bpy.ops.object.camera_add(
                location=(rad * 2.2, -rad * 2.2, cz + rad * 1.2))
            cam = bpy.context.active_object
            cam.rotation_euler = (math.radians(65), 0, math.radians(45))
            scn.camera = cam
            bpy.ops.object.light_add(
                type="SUN", location=(rad, -rad, rad * 3))
            bpy.context.active_object.data.energy = 4.0
            bpy.ops.render.render(write_still=True)
            print(f"PREVIEW: {a['preview']}")
        except Exception as exc:
            print(f"WARN preview: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
