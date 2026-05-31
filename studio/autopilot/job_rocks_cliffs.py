"""Job: scatter rocks + mossy boulders + cliffs for terrain breakup, near the
road, camp edges, and forest. Uses PolyHaven Nature_Rocks GLBs (Y-up) — placed
manually so the tree forest is untouched."""
import sys, json, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

ROCKS = [
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_01_Boulder1.glb",
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_02_Rock7.glb",
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_03_Rock9.glb",
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_06_RockMossSet.glb",
]
rng = random.Random(417)

# anchors: path nodes + camp + castle base
anchors = []
cf = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
anchors.append((cf[0], cf[2]))
ks = pos_of("GothicCastle", -482, 96, -311)
anchors.append((ks[0], ks[2]))
for i in range(7):
    p = pos_of(f"PathNode_{i:02d}")
    if p: anchors.append((p[0], p[2]))
print(f"ROCK anchors: {len(anchors)}")

for _ in range(2): rc("delete_object", {"name": "RockScatter"}, 10)
rc("create_empty", {"name": "RockScatter", "position": {"x": cf[0], "y": cf[1], "z": cf[2]}}, 12)

n = 0
rid = 0
for (ax, az) in anchors:
    for _ in range(3):  # 3 rocks per anchor
        dx = rng.uniform(-12, 12); dz = rng.uniform(-12, 12)
        rx, rz = ax+dx, az+dz
        asset = rng.choice(ROCKS)
        nm = f"Rock_{rid:03d}"; rid += 1
        sc = rng.uniform(1.2, 3.5)
        r = place_pinned(asset, rx, rz, sc, nm, parent="RockScatter", glb=True,
                         rot_y=rng.uniform(0, 360), y_offset=-0.3,
                         min_surface_y=5.0, max_slope_deg=60.0)
        if r:
            # mossy set keeps its look; others get a cool grey-stone tint
            if "Moss" not in asset:
                color(nm, 0.32, 0.31, 0.29, smooth=0.12)
            n += 1
print(f"ROCKS placed {n}")

# a few big cliff outcrops behind the castle for a dramatic backdrop
import os
CLIFF = "Assets/Art/HQ/cliff_outcrop.fbx"  # FBX (Z-up)
for i in range(3):
    a = math.pi*0.5 + (i-1)*0.5
    cx = ks[0]+math.cos(a)*40; cz = ks[2]+math.sin(a)*40
    nm = f"Cliff_{i}"
    r = place_pinned(CLIFF, cx, cz, rng.uniform(120, 180), nm, parent="RockScatter",
                     glb=False, rot_y=rng.uniform(0, 360), y_offset=-2.0,
                     min_surface_y=5.0, max_slope_deg=80.0)
    if r:
        color(nm, 0.30, 0.30, 0.32, smooth=0.10); n += 1
print(f"WITH CLIFFS total {n}")

d = rc("get_object_details", {"name": "WorldForestGLB"}, 15) or {}
print("FOREST still:", d.get("child_count"))
print("SAVE", save())
print("JOB_DONE rocks cliffs")
