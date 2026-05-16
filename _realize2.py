"""Phase 97: richer realism pass (compiled handlers only, no recompile).
Iterate fast here; fold the good result into studio_realize_world.
"""
import json, math, random
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

c, b, U = _bootstrap(); U.connect(timeout=6.0)
init_studio_unity(U); ut._UNITY = U
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
init_studio_tools(StudioState(P))
from unitytools.studio.tools import studio_capture_screenshot

def call(cmd, params, t=120):
    try: return U.call(cmd, params, timeout=t)
    except Exception as e: return {"ok": False, "error": str(e)[:150]}

call("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"})
roots = call("list_root_objects", {})
terr = next((r for r in roots.get("roots", []) if r["name"] == "WorldTerrain"), None)
tx, ty, tz = terr["pos"]
foot = abs(tx) * 2.0
cx, cz = tx + foot/2, tz + foot/2
relief = 1168.0

# 1) Naturalistic biomes — water-line band added at the very bottom
print("biomes:", json.dumps(call("repaint_terrain_biomes", {
    "plains_to": 0.30, "forest_to": 0.62, "rock_to": 0.88,
    "plains_color": [0.34, 0.45, 0.23], "forest_color": [0.15, 0.29, 0.15],
    "rock_color": [0.43, 0.41, 0.38], "snow_color": [0.93, 0.95, 0.98],
}))[:120])

# 2) Water — lower (valley floors), bigger, deep blue
wy = ty + 0.075 * relief
call("create_primitive", {"type": "Plane", "name": "WorldWater",
                          "position_x": cx, "position_y": wy, "position_z": cz})
call("set_scale", {"name": "WorldWater", "x": foot/9.0, "y": 1.0, "z": foot/9.0})
call("set_material_color", {"name": "WorldWater", "r": 0.04, "g": 0.16, "b": 0.24, "a": 1.0})
print("water y=", round(wy, 1))

# 3) Natural forest — two passes: dense-ish near water band + sparse mid
f1 = call("scatter_terrain_trees", {"tree_count": 320, "forest_min": 0.10,
          "forest_max": 0.34, "max_slope_deg": 26, "scale_min": 9,
          "scale_max": 18, "seed": 21})
print("forest low:", json.dumps(f1)[:120])
# second pass appends? scatter clears WorldForest each call -> instead
# rely on one wider call for natural spread
f2 = call("scatter_terrain_trees", {"tree_count": 360, "forest_min": 0.12,
          "forest_max": 0.50, "max_slope_deg": 30, "scale_min": 8,
          "scale_max": 17, "seed": 33})
print("forest final:", json.dumps(f2)[:120])

# 4) Boulders on mid slopes (procedural, grey, HDRP-safe via set_material_color)
random.seed(3)
nb = 0
for i in range(26):
    a = random.random()*math.tau; rr = random.uniform(0.12, 0.42)*foot
    bx, bz = cx + math.cos(a)*rr, cz + math.sin(a)*rr
    nm = f"Boulder_{i:02d}"
    r = call("create_primitive", {"type": "Sphere", "name": nm,
             "position_x": bx, "position_y": ty + 0.35*relief, "position_z": bz})
    if isinstance(r, dict) and r.get("ok"):
        s = random.uniform(14, 40)
        call("set_scale", {"name": nm, "x": s, "y": s*0.7, "z": s})
        call("set_material_color", {"name": nm, "r": 0.40, "g": 0.39, "b": 0.36, "a": 1.0})
        nb += 1
print("boulders:", nb)

# 5) Atmosphere + 6) smart camera
call("setup_hdrp_volume", {"exposure_mode": "Automatic", "fog": True, "fog_distance": 1800})
call("setup_smart_camera", {"target": "WorldTerrain", "pitch": 30, "yaw": 38, "distance_factor": 0.5})
call("save_scene", {})
print(json.dumps(studio_capture_screenshot(name="fv_realism2"))[:150])
print("REALISM2 DONE")
