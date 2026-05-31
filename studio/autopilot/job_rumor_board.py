"""Job: place a RumorBoard prop near the camp so the RumorBoard.cs interaction
has a world anchor. Built from primitives: two posts + a plank board."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

cf = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
# place near the campfire, a few metres toward the path
bx, bz = cf[0]+5, cf[2]-6
by = surf(bx, bz, cf[1])
print(f"BOARD {bx:.0f},{by:.0f},{bz:.0f}")

for _ in range(2): rc("delete_object", {"name": "RumorBoard"}, 10)
# root board object (this is what RumorBoard.cs finds by name)
rc("create_empty", {"name": "RumorBoard", "position": {"x": bx, "y": by, "z": bz}}, 12)

def child(prim, nm, x, y, z, sx, sy, sz, rotY=0, col=(0.20,0.12,0.06)):
    rc("create_primitive", {"type": prim, "name": nm,
        "position": {"x": x, "y": y, "z": z}, "scale": {"x": sx, "y": sy, "z": sz}}, 18)
    if rotY: rc("set_rotation", {"name": nm, "x": 0, "y": rotY, "z": 0}, 10)
    rc("set_parent", {"child": nm, "parent": "RumorBoard"}, 10)
    color(nm, col[0], col[1], col[2], smooth=0.12)

# two posts + board panel + a small roof
child("Cylinder", "RB_PostL", bx-0.8, by+1.0, bz, 0.12, 1.0, 0.12)
child("Cylinder", "RB_PostR", bx+0.8, by+1.0, bz, 0.12, 1.0, 0.12)
child("Cube",     "RB_Panel", bx, by+1.6, bz, 1.9, 1.1, 0.12, col=(0.26,0.17,0.09))
child("Cube",     "RB_Roof",  bx, by+2.25, bz, 2.2, 0.1, 0.5, col=(0.10,0.07,0.04))
# a couple of "note" squares pinned on the board
child("Cube", "RB_Note1", bx-0.4, by+1.7, bz+0.07, 0.35, 0.45, 0.02, col=(0.85,0.80,0.66))
child("Cube", "RB_Note2", bx+0.45, by+1.5, bz+0.07, 0.3, 0.38, 0.02, col=(0.80,0.74,0.6))

print("SAVE", save())
print("JOB_DONE rumor board")
