"""Job: Bridge Rest beat — a rest point partway along the path with a RestTotem
+ a LootChest (reward after risk). Placed at the midpoint of PathRoute."""
import sys, math, random, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *
PROJ = "D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0"

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

# midpoint of the path (node 3 of 0..6) else camp->castle mid
mid = pos_of("PathNode_03")
if mid is None:
    cf = pos_of("Campfire") or pos_of("WoodHouse", -533,138,-105)
    ks = pos_of("GothicCastle", -482,96,-311)
    mx, mz = (cf[0]+ks[0])/2, (cf[2]+ks[2])/2
    my = surf(mx, mz, cf[1]); mid = (mx, my, mz)
mx, my, mz = mid
print(f"REST {mx:.0f},{my:.0f},{mz:.0f}")

group("RestPoint", mx, my, mz)
n = 0

# RestTotem (generated FBX, Z-up -> glb=False)
TOTEM = "studio/assets/generated/RestTotem_Bridge/final.fbx"
if os.path.exists(f"{PROJ}/{TOTEM}"):
    rc("import_asset", {"src_path": f"{PROJ}/{TOTEM}", "dst_relative": "Art/HQ/RestTotem.fbx"}, 90)
    import time as _t; _t.sleep(2); fresh()
    r = place_pinned("Assets/Art/HQ/RestTotem.fbx", mx, mz, 2.4, "RestTotem",
                     parent="RestPoint", glb=False, rot_y=0, y_offset=0.0,
                     min_surface_y=5.0, max_slope_deg=40.0)
    if r: color("RestTotem", 0.26, 0.16, 0.09, smooth=0.12); n += 1
else:
    prim("Cylinder", "RestTotem", mx, my+1.5, mz, 0.6, 1.5, 0.6, parent="RestPoint", col=(0.26,0.16,0.09))
    n += 1

# soft rest light
light("RestGlow", "Point", 50.0, 12.0, (0.5, 0.75, 1.0), mx, my+2.0, mz, parent="RestPoint")

# LootChest (TreasureChest GLB, Y-up) a couple metres aside
chest = "Assets/FantasyRPG/Models/PolyHaven/Environment/Props/Environment_Props_01_TreasureChest.glb"
r = place_pinned(chest, mx+2.5, mz+1.0, 2.4, "LootChest", parent="RestPoint",
                 glb=True, rot_y=210, y_offset=0.0, min_surface_y=5.0, max_slope_deg=40.0)
if r:
    color("LootChest", 0.35, 0.22, 0.10, smooth=0.2)
    n += 1

print(f"RESTPOINT placed {n}")
print("children", child_count("RestPoint"))
print("FOREST", child_count("WorldForestGLB"))
print("SAVE", save())
print("JOB_DONE rest loot")
