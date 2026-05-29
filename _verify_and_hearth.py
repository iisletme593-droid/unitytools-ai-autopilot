"""Phase 98: (a) regression-verify the locked studio_realize_world
reliably reproduces the good green terrain; (b) add the GDD hearth —
the warm 'home' anchor (campfire + warm point light) at the terrain
centre valley. Compiled handlers only, no recompile.
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
    except Exception as e: return {"ok": False, "error": str(e)[:140]}

# (a) Regression: the committed orchestrator should now reliably make
# the believable green terrain (ensure-sun + Fixed-13 locked in).
r = studio_realize_world(water_level=0.085, forest_count=300, relief_m=1168.0)
print("REALIZE ok=", r.get("ok"), "applied_ok=", r.get("applied_ok"))

# (b) Hearth — GDD's warm home anchor. Place near terrain centre.
roots = call("list_root_objects", {})
terr = next((x for x in roots.get("roots", []) if x["name"] == "WorldTerrain"), None)
tx, ty, tz = terr["pos"]; foot = abs(tx)*2.0
cx, cz = tx+foot/2, tz+foot/2
hy = ty + 0.16*1168.0  # a low-mid valley shelf, above the waterline

call("create_primitive", {"type": "Cylinder", "name": "Hearth_Ring",
     "position_x": cx, "position_y": hy, "position_z": cz})
call("set_scale", {"name": "Hearth_Ring", "x": 6, "y": 0.6, "z": 6})
call("set_material_color", {"name": "Hearth_Ring", "r": 0.18, "g": 0.13,
     "b": 0.10, "a": 1.0})
call("create_primitive", {"type": "Cube", "name": "Hearth_Fire",
     "position_x": cx, "position_y": hy + 1.2, "position_z": cz})
call("set_scale", {"name": "Hearth_Fire", "x": 2.2, "y": 2.4, "z": 2.2})
call("set_material_color", {"name": "Hearth_Fire", "r": 1.0, "g": 0.5,
     "b": 0.15, "a": 1.0})
call("create_light", {"name": "Hearth_Glow", "light_type": "Point",
     "position_x": cx, "position_y": hy + 2.0, "position_z": cz,
     "r": 1.0, "g": 0.6, "b": 0.25, "intensity": 4.0, "range_val": 40})
call("set_light_properties", {"name": "Hearth_Glow", "intensity": 9000.0,
     "range_val": 60})
print("hearth placed at", round(cx), round(hy), round(cz))

# Camera: angle to include the hearth-centre valley
call("setup_smart_camera", {"target": "WorldTerrain", "pitch": 30,
     "yaw": 40, "distance_factor": 0.5})
call("save_scene", {})
print(json.dumps(studio_capture_screenshot(name="fv_hearth"))[:150])
print("HEARTH DONE")
