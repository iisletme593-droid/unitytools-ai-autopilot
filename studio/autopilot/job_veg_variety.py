"""Job: ambient vegetation variety WITHOUT touching the tree forest.
CRITICAL: scatter_terrain_glb_trees DESTROYS WorldForestGLB on every call, so we
must NOT use it for ferns. Instead: place hero ferns in clusters near the camp +
along the road (where the player sees them), plus safe grass ground cover
(scatter_terrain_grass uses a separate WorldGrass group)."""
import sys, json, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *
PROJ = "D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0"

connect()
if not guard_scene():
    print("GUARD_FAIL"); sys.exit(1)

rc("import_asset", {"src_path": f"{PROJ}/studio/assets/hq/Fern/final.glb",
                    "dst_relative": "Art/HQ/Fern.glb"}, 90)
import time as _t; _t.sleep(2); fresh()

FERN = "Assets/Art/HQ/Fern.glb"
rng = random.Random(331)

# cluster anchors: camp + a few path nodes + forest edge points
anchors = []
cf = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
anchors.append((cf[0], cf[2]))
for i in range(7):
    p = pos_of(f"PathNode_{i:02d}")
    if p: anchors.append((p[0], p[2]))
print(f"FERN anchors: {len(anchors)}")

for _ in range(2): rc("delete_object", {"name": "FernUndergrowth"}, 10)
rc("create_empty", {"name": "FernUndergrowth", "position": {"x": cf[0], "y": cf[1], "z": cf[2]}}, 12)

n = 0
fid = 0
for (ax, az) in anchors:
    for _ in range(6):  # ~6 ferns per cluster
        dx = rng.uniform(-7, 7); dz = rng.uniform(-7, 7)
        fx, fz = ax+dx, az+dz
        nm = f"Fern_{fid:03d}"; fid += 1
        r = place_pinned(FERN, fx, fz, rng.uniform(1.0, 2.2), nm,
                         parent="FernUndergrowth", glb=True,
                         rot_y=rng.uniform(0, 360), y_offset=-0.1,
                         min_surface_y=5.0, max_slope_deg=34.0)
        if r:
            color(nm, 0.16, 0.30, 0.11, smooth=0.16)  # fern green
            n += 1
print(f"FERNS placed {n}")

# safe broad grass ground cover (separate WorldGrass group)
g = rc("scatter_terrain_grass", {"clump_count": 4000, "band_min": 0.04, "band_max": 0.5,
       "max_slope_deg": 34.0, "scale_min": 4.0, "scale_max": 9.0, "seed": 332}, 120)
print("GRASS:", json.dumps({k: g.get(k) for k in ("placed",)} if isinstance(g, dict) else {}))

# confirm the forest survived
d = rc("get_object_details", {"name": "WorldForestGLB"}, 15) or {}
print("FOREST still:", d.get("child_count"))

print("SAVE", save())
print("JOB_DONE veg variety")
