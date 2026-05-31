"""Job: enrich the camp with real props (weapon rack, war banner, crafting
bench, tables, stools, buckets) around the campfire. Uses ap.py helpers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *
PROJ = "D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0"

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

# anchor on campfire (fallback to house)
fp = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
fx, fy, fz = fp
print(f"FIRE {fx:.0f},{fy:.0f},{fz:.0f}")

# import generated FBX camp assets (Z-up -> glb=False => rotx -90)
gen = {
  "WeaponRack": "studio/assets/generated/WeaponRack_Camp/final.fbx",
  "WarBanner":  "studio/assets/generated/WarBanner_Camp/final.fbx",
  "CraftBench": "studio/assets/generated/CraftingBench_Camp/final.fbx",
}
for nm, rel in gen.items():
    rc("import_asset", {"src_path": f"{PROJ}/{rel}", "dst_relative": f"Art/HQ/{nm}.fbx"}, 90)
import time as _t; _t.sleep(2); fresh()

# GLB furniture/props from PolyHaven (Y-up -> glb=True)
PH = "Assets/FantasyRPG/Models/PolyHaven/Environment"
glb = {
  "Table1": f"{PH}/Furniture/Environment_Furniture_09_WoodenTable1.glb",
  "Stool1": f"{PH}/Furniture/Environment_Furniture_12_WoodenStool.glb",
  "Stool2": f"{PH}/Furniture/Environment_Furniture_12_WoodenStool.glb",
  "Bucket": f"{PH}/Props/Environment_Props_08_WoodenBucket1.glb",
  "WLantern": f"{PH}/Lighting/Environment_Lighting_02_WoodenLantern.glb",
}

# clear + recreate the dressing group (idempotent)
for _ in range(2): rc("delete_object", {"name": "CampDressing"}, 10)
rc("create_empty", {"name": "CampDressing", "position": {"x": fx, "y": fy, "z": fz}}, 12)

n = 0
# generated FBX (rotx -90)
layout_fbx = [
    ("WeaponRack", "Art/HQ/WeaponRack.fbx", -8, 6, 2.0, 90),
    ("WarBanner",  "Art/HQ/WarBanner.fbx",  -6, 12, 2.4, 20),
    ("CraftBench", "Art/HQ/CraftBench.fbx",  9, 12, 2.0, 250),
]
for nm, asset, dx, dz, sc, ry in layout_fbx:
    r = place_pinned("Assets/" + asset, fx+dx, fz+dz, sc, nm,
                     parent="CampDressing", glb=False, rot_y=ry, y_offset=0.0)
    if r: n += 1; print(f"  placed {nm}")

# GLB props (rotx 0)
layout_glb = [
    ("Table1", glb["Table1"], 5, 4, 2.2, 30),
    ("Stool1", glb["Stool1"], 4, 6, 2.2, 0),
    ("Stool2", glb["Stool2"], 7, 5, 2.2, 120),
    ("Bucket", glb["Bucket"], -3, 7, 2.2, 0),
    ("WLantern", glb["WLantern"], 2, 9, 2.4, 0),
]
for nm, asset, dx, dz, sc, ry in layout_glb:
    r = place_pinned(asset, fx+dx, fz+dz, sc, nm,
                     parent="CampDressing", glb=True, rot_y=ry, y_offset=0.0)
    if r: n += 1; print(f"  placed {nm}")

# warm colour pass on the wood-y generated props
for nm in ["WeaponRack", "CraftBench"]:
    color(nm, 0.26, 0.16, 0.09, smooth=0.12)
color("WarBanner", 0.45, 0.12, 0.10, smooth=0.15)  # dry-blood red banner

print(f"DRESSING placed {n}")
print("SAVE", save())
print("JOB_DONE camp props")
