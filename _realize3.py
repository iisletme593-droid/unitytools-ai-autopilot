"""Phase 97b: revert to the KNOWN-GOOD green look (Phase 96 params:
FIXED exposure ~12.5, camera df 0.55, fog 2200) + keep the additive
wins (valley water, richer forest). Automatic exposure was unstable.
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
from unitytools.studio.tools import studio_capture_screenshot

def call(cmd, p, t=120):
    try: return U.call(cmd, p, timeout=t)
    except Exception as e: return {"ok": False, "error": str(e)[:140]}

call("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"})
roots = call("list_root_objects", {})
terr = next((r for r in roots.get("roots", []) if r["name"] == "WorldTerrain"), None)
tx, ty, tz = terr["pos"]; foot = abs(tx)*2.0
cx, cz = tx+foot/2, tz+foot/2; relief = 1168.0

# Known-good green biomes (Phase 96 fv_realized values)
call("repaint_terrain_biomes", {
    "plains_to": 0.34, "forest_to": 0.66, "rock_to": 0.90,
    "plains_color": [0.33, 0.44, 0.22], "forest_color": [0.16, 0.30, 0.15],
    "rock_color": [0.42, 0.40, 0.37], "snow_color": [0.92, 0.94, 0.97]})

# keep water (valley floors)
wy = ty + 0.085*relief
call("create_primitive", {"type": "Plane", "name": "WorldWater",
     "position_x": cx, "position_y": wy, "position_z": cz})
call("set_scale", {"name": "WorldWater", "x": foot/9.0, "y": 1.0, "z": foot/9.0})
call("set_material_color", {"name": "WorldWater", "r": 0.05, "g": 0.17, "b": 0.25, "a": 1.0})

# richer-but-natural forest (single wide pass = clean)
print("forest:", json.dumps(call("scatter_terrain_trees", {
    "tree_count": 300, "forest_min": 0.14, "forest_max": 0.52,
    "max_slope_deg": 31, "scale_min": 8, "scale_max": 16, "seed": 11}))[:120])

# FIXED exposure (stable green, not the washed-out Automatic) + fog 2200
print("exp:", json.dumps(call("setup_hdrp_volume", {
    "exposure_mode": "Fixed", "fixed_exposure": 12.5,
    "fog": True, "fog_distance": 2200}))[:160])

# the Phase-96 good camera framing
call("setup_smart_camera", {"target": "WorldTerrain", "pitch": 32,
     "yaw": 40, "distance_factor": 0.55})
call("save_scene", {})
print(json.dumps(studio_capture_screenshot(name="fv_green_good"))[:150])
print("REALIZE3 DONE")
