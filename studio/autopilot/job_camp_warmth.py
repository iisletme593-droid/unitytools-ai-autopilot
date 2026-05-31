"""Job: cozy campfire pocket — log seats ringing the fire, warm light pools,
a couple of stools/buckets, gentle ember glow. Uses primitives for log seats
(reliable) + warm point lights."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

fp = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
fx, fy, fz = fp
print(f"FIRE {fx:.0f},{fy:.0f},{fz:.0f}")

for _ in range(2): rc("delete_object", {"name": "CampWarmth"}, 10)
rc("create_empty", {"name": "CampWarmth", "position": {"x": fx, "y": fy, "z": fz}}, 12)

n = 0
# Log seats: short fat cylinders ringing the fire at ~3.5m radius
for i in range(5):
    a = (i/5)*math.tau + 0.3
    lx, lz = fx+math.cos(a)*3.6, fz+math.sin(a)*3.6
    ly = surf(lx, lz, fy)
    nm = f"LogSeat_{i}"
    rc("create_primitive", {"type": "Cylinder", "name": nm,
        "position": {"x": lx, "y": ly+0.35, "z": lz},
        "scale": {"x": 0.7, "y": 0.35, "z": 0.7}}, 18)
    rc("set_rotation", {"name": nm, "x": 90, "y": math.degrees(a), "z": 0}, 10)
    rc("set_parent", {"child": nm, "parent": "CampWarmth"}, 10)
    color(nm, 0.18, 0.11, 0.06, smooth=0.12)
    n += 1

# Bedroll: a flat low box near the fire
bx, bz = fx-4, fz-3
by = surf(bx, bz, fy)
rc("create_primitive", {"type": "Cube", "name": "Bedroll",
    "position": {"x": bx, "y": by+0.12, "z": bz},
    "scale": {"x": 1.0, "y": 0.18, "z": 2.0}}, 18)
rc("set_rotation", {"name": "Bedroll", "x": 0, "y": 35, "z": 0}, 10)
rc("set_parent", {"child": "Bedroll", "parent": "CampWarmth"}, 10)
color("Bedroll", 0.30, 0.22, 0.12, smooth=0.18)
n += 1

# Warm light pools: a strong core fire light + 2 soft fill pools
light("FireCore", "Point", 200.0, 16.0, (1.0, 0.5, 0.18), fx, fy+1.4, fz)
light("FirePool1", "Point", 60.0, 11.0, (1.0, 0.62, 0.3), fx+4, fy+1.0, fz+2)
light("FirePool2", "Point", 45.0, 10.0, (1.0, 0.6, 0.28), fx-3, fy+1.0, fz-2)
for nm in ["FireCore", "FirePool1", "FirePool2"]:
    rc("set_parent", {"child": nm, "parent": "CampWarmth"}, 10)

print(f"WARMTH placed {n} props + 3 lights")
print("SAVE", save())
print("JOB_DONE camp warmth")
