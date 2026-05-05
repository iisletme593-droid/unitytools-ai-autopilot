"""Blender FBX export — `blender --background X.blend --python export_fbx.py -- output.fbx [opts]`

Argümanlar:
    output_path           hedef .fbx dosyası (zorunlu, ilk argüman)
    --slot NAME           sadece ismi NAME'i içeren objeleri export et
    --objects A,B,C       sadece bu objeleri export et
    --scale 1.0           export scale
    --no-anim             animasyonu export etme
"""
import os
import sys
from pathlib import Path

import bpy


def parse_args() -> dict | None:
    try:
        sep = sys.argv.index("--")
        args = sys.argv[sep + 1 :]
    except ValueError:
        print("ERROR: '--' separator yok")
        return None

    if not args:
        print("ERROR: output_path argümanı zorunlu")
        return None

    out: dict = {"output_path": args[0], "slot": None, "objects": None, "scale": 1.0, "bake_anim": True}

    i = 1
    while i < len(args):
        a = args[i]
        if a == "--slot" and i + 1 < len(args):
            out["slot"] = args[i + 1]
            i += 2
        elif a == "--objects" and i + 1 < len(args):
            out["objects"] = [s.strip() for s in args[i + 1].split(",") if s.strip()]
            i += 2
        elif a == "--scale" and i + 1 < len(args):
            out["scale"] = float(args[i + 1])
            i += 2
        elif a == "--no-anim":
            out["bake_anim"] = False
            i += 1
        else:
            i += 1
    return out


def select_by_slot(slot: str) -> int:
    bpy.ops.object.select_all(action="DESELECT")
    n = 0
    for obj in bpy.data.objects:
        if slot.lower() in obj.name.lower():
            obj.select_set(True)
            n += 1
    return n


def select_by_names(names: list[str]) -> int:
    bpy.ops.object.select_all(action="DESELECT")
    n = 0
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.select_set(True)
            n += 1
        else:
            print(f"WARN: object yok: {name}")
    return n


def main() -> int:
    args = parse_args()
    if args is None:
        return 1

    output_path = args["output_path"]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    selected_only = False
    if args["slot"]:
        n = select_by_slot(args["slot"])
        if n == 0:
            print(f"WARN: slot '{args['slot']}' eşleşen obje yok, scene'in tamamı export edilecek")
        else:
            selected_only = True
            print(f"INFO: slot '{args['slot']}' için {n} obje seçildi")
    elif args["objects"]:
        n = select_by_names(args["objects"])
        if n > 0:
            selected_only = True
            print(f"INFO: {n} obje seçildi")

    settings = {
        "filepath": output_path,
        "use_selection": selected_only,
        "global_scale": args["scale"],
        "apply_unit_scale": True,
        "apply_scale_options": "FBX_SCALE_ALL",
        "object_types": {"MESH", "ARMATURE", "EMPTY"},
        "use_mesh_modifiers": True,
        "mesh_smooth_type": "FACE",
        "use_tspace": True,
        "add_leaf_bones": False,
        "primary_bone_axis": "Y",
        "secondary_bone_axis": "X",
        "bake_anim": args["bake_anim"],
        "bake_anim_use_all_bones": True,
        "bake_anim_use_nla_strips": True,
        "bake_anim_use_all_actions": True,
        "path_mode": "AUTO",
        "embed_textures": False,
        "axis_forward": "-Z",
        "axis_up": "Y",
    }

    try:
        bpy.ops.export_scene.fbx(**settings)
    except Exception as e:
        print(f"ERROR: FBX export başarısız: {e}")
        return 1

    if not os.path.exists(output_path):
        print("ERROR: çıktı dosyası oluşmadı")
        return 1

    print(f"OK: {output_path} ({os.path.getsize(output_path):,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
