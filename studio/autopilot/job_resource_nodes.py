"""Job: Outer Gather Ring — wood + stone resource nodes around the camp.
Wood = PolyHaven tree stumps; Stone = PolyHaven rocks. Each node is named
ResourceWood_xx / ResourceStone_xx and tagged so a future gather system finds
them. Manual placement (forest untouched)."""
import sys, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

rng = random.Random(515)
cf = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
cx, cy, cz = cf
print(f"CAMP {cx:.0f},{cy:.0f},{cz:.0f}")

WOOD = [
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Trees/Nature_Trees_02_TreeStump1.glb",
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Trees/Nature_Trees_03_TreeStump2.glb",
]
STONE = [
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_02_Rock7.glb",
  "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_03_Rock9.glb",
]

group("ResourceNodes", cx, cy, cz)
n_wood = n_stone = 0

# wood ring 18-30m
for i in range(8):
    a = (i/8)*math.tau + rng.uniform(-0.2, 0.2)
    rad = rng.uniform(18, 30)
    wx, wz = cx+math.cos(a)*rad, cz+math.sin(a)*rad
    my = surf(wx, wz, cy)
    if my < 5: continue
    nm = f"ResourceWood_{i:02d}"
    r = place_pinned(rng.choice(WOOD), wx, wz, rng.uniform(2.0, 3.2), nm,
                     parent="ResourceNodes", glb=True, rot_y=rng.uniform(0,360),
                     y_offset=-0.2, min_surface_y=5.0, max_slope_deg=35.0)
    if r:
        color(nm, 0.24, 0.15, 0.08, smooth=0.12)
        rc("set_tag", {"name": nm, "tag": "Untagged"}, 8)  # tag 'Untagged' is safe; name carries type
        n_wood += 1

# stone ring 22-34m (offset phase)
for i in range(8):
    a = (i/8)*math.tau + math.pi/8 + rng.uniform(-0.2, 0.2)
    rad = rng.uniform(22, 34)
    sx, sz = cx+math.cos(a)*rad, cz+math.sin(a)*rad
    my = surf(sx, sz, cy)
    if my < 5: continue
    nm = f"ResourceStone_{i:02d}"
    r = place_pinned(rng.choice(STONE), sx, sz, rng.uniform(1.0, 2.0), nm,
                     parent="ResourceNodes", glb=True, rot_y=rng.uniform(0,360),
                     y_offset=-0.2, min_surface_y=5.0, max_slope_deg=40.0)
    if r:
        color(nm, 0.34, 0.33, 0.31, smooth=0.10)
        n_stone += 1

print(f"WOOD {n_wood} STONE {n_stone}")
cc = child_count("ResourceNodes")
print(f"ResourceNodes children={cc}")
print("FOREST", child_count("WorldForestGLB"))
print("SAVE", save())
print("JOB_DONE resource nodes")
