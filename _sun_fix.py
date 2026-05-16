"""Root cause: scene had NO light at all. Create a proper HDRP
directional sun + pair with fixed exposure. Self-iterate exposure
until the green reads right (screenshots work now).
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
from unitytools.tools.unity_tools import (
    unity_open_scene, unity_save_scene, unity_create_light,
    unity_set_light_properties, unity_set_rotation, unity_list_lights)
from unitytools.studio.tools import studio_capture_screenshot

def call(cmd, p, t=120):
    try: return U.call(cmd, p, timeout=t)
    except Exception as e: return {"ok": False, "error": str(e)[:140]}

unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")

# Create the sun (none exists). Warm overcast-daylight directional.
r = unity_create_light("Sun", "Directional", 0, 500, 0,
                        1.0, 0.96, 0.88, 1.0, 200)
print("create sun:", json.dumps(r)[:140])
unity_set_rotation("Sun", 48, -34, 0)
# HDRP daylight ~ tens of thousands of lux; the bridge maps intensity.
unity_set_light_properties(name="Sun", intensity=22000.0, shadows_enabled=1,
                           shadow_strength=0.7)
print("lights now:", json.dumps(unity_list_lights())[:160])

call("setup_hdrp_volume", {"exposure_mode": "Fixed", "fixed_exposure": 13.0,
                           "fog": True, "fog_distance": 2200})
call("setup_smart_camera", {"target": "WorldTerrain", "pitch": 32,
                            "yaw": 40, "distance_factor": 0.55})
unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_sun"))[:150])
print("SUN FIX DONE")
