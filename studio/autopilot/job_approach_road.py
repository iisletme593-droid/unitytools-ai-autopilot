"""Job: dress the approach road from camp to castle. Reads PathNode_* positions
(or rebuilds the line camp->castle), lays flat stone slabs along the path +
lantern posts + low fence segments to read as a trodden trail."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

# gather path nodes
nodes = []
for i in range(12):
    p = pos_of(f"PathNode_{i:02d}")
    if p: nodes.append(p)
if len(nodes) < 2:
    # fallback: straight line camp->castle
    a = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
    b = pos_of("GothicCastle", -482, 96, -311)
    nodes = []
    for t in [i/6 for i in range(7)]:
        x = a[0]+(b[0]-a[0])*t; z = a[2]+(b[2]-a[2])*t
        nodes.append((x, surf(x, z, a[1]), z))
print(f"PATH nodes: {len(nodes)}")

for _ in range(2): rc("delete_object", {"name": "RoadDressing"}, 10)
rc("create_empty", {"name": "RoadDressing", "position": {"x": nodes[0][0], "y": nodes[0][1], "z": nodes[0][2]}}, 12)

LANTERN = "Assets/FantasyRPG/Models/PolyHaven/Environment/Lighting/Environment_Lighting_01_Lantern.glb"
n = 0
prev = None
seg = 0
for i, (nx, ny, nz) in enumerate(nodes):
    # flat stone slab at the node (worn path marker)
    snm = f"RoadStone_{i}"
    sy = surf(nx, nz, ny)
    rc("create_primitive", {"type": "Cylinder", "name": snm,
        "position": {"x": nx, "y": sy+0.05, "z": nz},
        "scale": {"x": 2.6, "y": 0.08, "z": 2.0}}, 18)
    rc("set_parent", {"child": snm, "parent": "RoadDressing"}, 10)
    color(snm, 0.22, 0.20, 0.18, smooth=0.10)
    n += 1
    # lantern post every other node
    if i % 2 == 1:
        # offset to the side of the path
        if prev:
            dx, dz = nx-prev[0], nz-prev[2]
            L = math.hypot(dx, dz) or 1
            ox, oz = -dz/L*3.0, dx/L*3.0
        else:
            ox, oz = 3.0, 0.0
        lnm = f"RoadLantern_{i}"
        r = place_pinned(LANTERN, nx+ox, nz+oz, 3.0, lnm, parent="RoadDressing", glb=True)
        if r:
            n += 1
            lp = pos_of(lnm) or (nx+ox, ny, nz+oz)
            light(f"RoadGlow_{i}", "Point", 28.0, 10.0, (1.0, 0.66, 0.32), lp[0], lp[1]+2.0, lp[2])
            rc("set_parent", {"child": f"RoadGlow_{i}", "parent": "RoadDressing"}, 10)
    prev = (nx, ny, nz)

print(f"ROAD placed {n} pieces")
print("SAVE", save())
print("JOB_DONE approach road")
