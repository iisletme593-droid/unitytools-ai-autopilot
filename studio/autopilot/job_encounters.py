"""Job: encounter markers along the route per the play loop. Named empties a
spawn director can read: NorthAmbush (Briarbound), RotfangRun (RotfangWolf),
ShrinePressure (RootAcolyte). Placed at fractions along PathRoute. Also a
DungeonGate marker near the castle (Old Shrine Gate)."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

# path endpoints
cf = pos_of("Campfire") or pos_of("WoodHouse", -533,138,-105)
ks = pos_of("GothicCastle", -482,96,-311)
cx, cy, cz = cf

def on_path(t):
    px, pz = cx+(ks[0]-cx)*t, cz+(ks[2]-cz)*t
    return px, surf(px, pz, cy), pz

group("EncounterMarkers", cx, cy, cz)
# (name, enemy, t, count)
beats = [
    ("NorthAmbush",   "Briarbound", 0.25, 2),
    ("RotfangRun",    "RotfangWolf", 0.55, 3),
    ("ShrinePressure","RootAcolyte", 0.80, 3),
]
n = 0
for name, enemy, t, cnt in beats:
    bx, by, bz = on_path(t)
    # a parent beat marker + per-spawn child points spread around it
    empty(name, bx, by+0.5, bz, parent="EncounterMarkers")
    rc("set_tag", {"name": name, "tag": "Untagged"}, 8)
    for j in range(cnt):
        a = (j/cnt)*math.tau
        sx, sz = bx+math.cos(a)*4, bz+math.sin(a)*4
        sy = surf(sx, sz, by)
        empty(f"{name}_Spawn_{j}", sx, sy+0.5, sz, parent=name)
    n += 1
    print(f"  beat {name} ({enemy}) @ {bx:.0f},{bz:.0f} x{cnt}")

# Dungeon/shrine gate marker near the castle approach
gx, gy, gz = on_path(0.92)
empty("DungeonGate_OldShrine", gx, gy+0.5, gz, parent="EncounterMarkers")

print(f"ENCOUNTERS {n} beats + gate")
print("children", child_count("EncounterMarkers"))
print("FOREST", child_count("WorldForestGLB"))
print("SAVE", save())
print("JOB_DONE encounters")
