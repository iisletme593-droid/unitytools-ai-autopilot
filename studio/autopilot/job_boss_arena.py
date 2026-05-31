"""Job: boss arena as a sealed combat space, readable from the vista. Place it
on flat-ish ground between the castle and camp: a ring of cliff/rock 'walls'
enclosing an open floor, a focal centre (stone circle + totem + braziers),
and a BossSpawn marker. Manual placement (forest untouched)."""
import sys, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

rng = random.Random(909)
# centre: between castle and camp, biased toward the castle side
ks = pos_of("GothicCastle", -482, 96, -311)
cf = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
cx = ks[0]*0.6 + cf[0]*0.4
cz = ks[2]*0.6 + cf[2]*0.4
cy = surf(cx, cz, ks[1])
print(f"ARENA centre {cx:.0f},{cy:.0f},{cz:.0f}")

for _ in range(2): rc("delete_object", {"name": "BossArena"}, 10)
rc("create_empty", {"name": "BossArena", "position": {"x": cx, "y": cy, "z": cz}}, 12)

CLIFF = "Assets/Art/HQ/cliff_outcrop.fbx"  # FBX (Z-up -> glb=False)
ROCK = "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks/Nature_Rocks_04_RockFace1.glb"
RADIUS = 26.0
n = 0

# enclosing wall: alternating cliffs + rock faces around the ring (gap on the
# camp-facing side as the entrance)
count = 12
for i in range(count):
    a = (i/count)*math.tau
    # leave an entrance gap facing the camp
    entrance_dir = math.atan2(cf[2]-cz, cf[0]-cx)
    if abs(((a-entrance_dir+math.pi) % math.tau) - math.pi) < 0.5:
        continue  # skip -> doorway
    wx = cx + math.cos(a)*RADIUS
    wz = cz + math.sin(a)*RADIUS
    if i % 2 == 0:
        nm = f"ArenaWall_{i}"
        r = place_pinned(CLIFF, wx, wz, rng.uniform(150, 200), nm, parent="BossArena",
                         glb=False, rot_y=math.degrees(a)+90, y_offset=-2.0,
                         min_surface_y=5.0, max_slope_deg=85.0)
        if r: color(nm, 0.28, 0.28, 0.30, smooth=0.10); n += 1
    else:
        nm = f"ArenaRock_{i}"
        r = place_pinned(ROCK, wx, wz, rng.uniform(2.5, 4.0), nm, parent="BossArena",
                         glb=True, rot_y=rng.uniform(0,360), y_offset=-0.4,
                         min_surface_y=5.0, max_slope_deg=85.0)
        if r: color(nm, 0.30, 0.29, 0.27, smooth=0.10); n += 1

# focal centre: a low stone circle (ring of flat slabs) + a totem + 2 braziers
for i in range(8):
    a = (i/8)*math.tau
    sx = cx + math.cos(a)*4.5; sz = cz + math.sin(a)*4.5
    sy = surf(sx, sz, cy)
    nm = f"ArenaGlyph_{i}"
    rc("create_primitive", {"type": "Cylinder", "name": nm,
        "position": {"x": sx, "y": sy+0.06, "z": sz}, "scale": {"x": 1.1, "y": 0.1, "z": 1.1}}, 18)
    rc("set_parent", {"child": nm, "parent": "BossArena"}, 10)
    color(nm, 0.22, 0.20, 0.20, smooth=0.08); n += 1

# central totem (use RestTotem if available, else a stacked primitive)
import os
TOTEM = "studio/assets/generated/RestTotem_Shrine/final.fbx"
PROJ = "D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0"
if os.path.exists(f"{PROJ}/{TOTEM}"):
    rc("import_asset", {"src_path": f"{PROJ}/{TOTEM}", "dst_relative": "Art/HQ/BossTotem.fbx"}, 90)
    import time as _t; _t.sleep(2); fresh()
    r = place_pinned("Assets/Art/HQ/BossTotem.fbx", cx, cz, 2.6, "ArenaTotem",
                     parent="BossArena", glb=False, rot_y=0, y_offset=0.0,
                     min_surface_y=5.0, max_slope_deg=89.0)
    if r: color("ArenaTotem", 0.24, 0.15, 0.09, smooth=0.12); n += 1
else:
    rc("create_primitive", {"type": "Cylinder", "name": "ArenaTotem",
        "position": {"x": cx, "y": cy+2.0, "z": cz}, "scale": {"x": 0.8, "y": 2.0, "z": 0.8}}, 18)
    rc("set_parent", {"child": "ArenaTotem", "parent": "BossArena"}, 10)
    color("ArenaTotem", 0.24, 0.15, 0.09, smooth=0.12); n += 1

# two braziers (emberglow) flanking the centre
for i, dx in enumerate((-3.5, 3.5)):
    bx, bz = cx+dx, cz
    by = surf(bx, bz, cy)
    nm = f"ArenaBrazier_{i}"
    rc("create_primitive", {"type": "Cylinder", "name": nm,
        "position": {"x": bx, "y": by+0.6, "z": bz}, "scale": {"x": 0.5, "y": 0.6, "z": 0.5}}, 18)
    rc("set_parent", {"child": nm, "parent": "BossArena"}, 10)
    color(nm, 0.15, 0.13, 0.12, smooth=0.1)
    light(f"ArenaFire_{i}", "Point", 90.0, 14.0, (1.0, 0.45, 0.18), bx, by+1.4, bz)
    rc("set_parent", {"child": f"ArenaFire_{i}", "parent": "BossArena"}, 10)
    n += 1

# BossSpawn marker at the centre
empty("BossSpawn", cx, cy+0.5, cz, parent="BossArena")

print(f"ARENA placed {n} pieces")
d = rc("get_object_details", {"name": "WorldForestGLB"}, 15) or {}
print("FOREST still:", d.get("child_count"))
print("SAVE", save())
print("JOB_DONE boss arena")
