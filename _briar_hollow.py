"""Briar Hollow vertical-slice blockout (real DOCS P0 tasks):
make_terrain_playable (1.2km, hero on surface) -> realize world at
that scale -> first-playable-route blockout (spawn/camp-hearth/path/
landmark/mini-boss arena) -> screenshot. Autonomous, self-verified.
"""
import json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

c, b, U = _bootstrap(); U.connect(timeout=6.0)
init_studio_unity(U); ut._UNITY = U
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
init_studio_tools(StudioState(P))
from unitytools.studio.tools import studio_realize_world, studio_capture_screenshot

def call(cmd, p, t=120):
    try: return U.call(cmd, p, timeout=t)
    except Exception as e: return {"ok": False, "error": str(e)[:150]}

call("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"})

# 1) PLAYABLE SCALE — make_terrain_playable (compiled per user 'basla').
mp = call("make_terrain_playable", {"footprint_m": 1200, "relief_scale": 0.16,
          "character": "SK_Hero", "character_scale": 1.0})
print("PLAYABLE:", json.dumps(mp)[:300] if isinstance(mp, dict) else str(mp)[:300])
if isinstance(mp, dict) and "Unknown method" in str(mp.get("error", "")):
    print("make_terrain_playable NOT COMPILED yet — need Unity focus"); raise SystemExit(2)

# 2) Realize world at the new 1.2km scale (adapts; ensure-sun locked).
rw = studio_realize_world(water_level=0.085, forest_count=260, relief_m=190.0)
print("REALIZE ok=", rw.get("ok"), "applied_ok=", rw.get("applied_ok"))

# spawn world pos from make_terrain_playable ("x,y,z")
spawn = (mp.get("spawn") or "0,0,0").split(",")
sx, sy, sz = (float(spawn[0]), float(spawn[1]), float(spawn[2])) if len(spawn) == 3 else (0., 100., 0.)

def marker(name, dx, dz, prim, sx_, sy_, sz_, col):
    x, z = sx + dx, sz + dz
    call("create_primitive", {"type": prim, "name": name,
         "position_x": x, "position_y": sy + sy_*0.5 + 1.0, "position_z": z})
    call("set_scale", {"name": name, "x": sx_, "y": sy_, "z": sz_})
    call("set_material_color", {"name": name, "r": col[0], "g": col[1],
         "b": col[2], "a": 1.0})

# 3) FIRST PLAYABLE ROUTE blockout (spawn -> camp -> path -> landmark)
# Spawn pad
marker("Route_Spawn", 0, 0, "Cylinder", 4, 0.4, 4, (0.30, 0.50, 0.65))
# Camp / hearth a short walk from spawn (the Valheim 'home' anchor)
marker("Camp_HearthRing", 18, 10, "Cylinder", 6, 0.5, 6, (0.20, 0.14, 0.10))
marker("Camp_Fire", 18, 10, "Cube", 1.8, 2.4, 1.8, (1.0, 0.5, 0.15))
call("create_light", {"name": "Camp_Glow", "light_type": "Point",
     "position_x": sx+18, "position_y": sy+3, "position_z": sz+10,
     "r": 1.0, "g": 0.6, "b": 0.25, "intensity": 4, "range_val": 30})
call("set_light_properties", {"name": "Camp_Glow", "intensity": 8000.0, "range_val": 45})
# Path stones spawn -> landmark
for i in range(1, 7):
    marker(f"Path_{i:02d}", i*9, 6 + i*7, "Cube", 2.2, 0.3, 2.2, (0.32, 0.30, 0.27))
# Landmark — a tall distinctive spire (Briar Hollow read)
marker("Landmark_Spire", 64, 52, "Cylinder", 5, 26, 5, (0.22, 0.20, 0.24))
# Mini-boss arena — a flat clearing ring + central marker
marker("Boss_ArenaRing", 95, 78, "Cylinder", 22, 0.3, 22, (0.16, 0.12, 0.10))
marker("Boss_Marker", 95, 78, "Cube", 3, 5, 3, (0.55, 0.10, 0.12))

# 4) Final third-person cam on the hero (make_terrain_playable set it,
# realize may have moved it -> re-assert playable cam)
call("make_terrain_playable", {"footprint_m": 1200, "relief_scale": 0.16,
     "character": "SK_Hero", "character_scale": 1.0})
call("save_scene", {})
print(json.dumps(studio_capture_screenshot(name="fv_briar_hollow"))[:150])
print("BRIAR HOLLOW BLOCKOUT DONE")
