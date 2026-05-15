"""Tune the frame to a readable moody-realistic shot now that the
capture path is URP-correct. No reinstall needed — all runtime RPCs.
"""
import json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

c, b, unity = _bootstrap(); unity.connect(timeout=4.0)
init_studio_unity(unity); ut._UNITY = unity
p = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in p.all_dirs()]
init_studio_tools(StudioState(p))

from unitytools.tools.unity_tools import (
    unity_open_scene, unity_list_scenes, unity_set_camera_transform,
    unity_set_fog, unity_set_ambient_light, unity_set_light_properties,
    unity_set_rotation, unity_set_skybox, unity_create_primitive,
    unity_set_scale, unity_set_material_color, unity_save_scene,
)
from unitytools.studio.tools import studio_capture_screenshot

# scene-revert guard
unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")
act = [s for s in unity_list_scenes().get("scenes", []) if s.get("active")]
print("active:", act[0]["name"] if act else "?")

def s(label, r):
    ok = isinstance(r, dict) and r.get("ok", True)
    print(("OK  " if ok else "ERR ") + label + ("" if ok else f"  {r}"))

# 1) Player-eye third-person framing: low + close, slight down tilt,
#    looking toward the sealed pass (+Z) past the hearth.
s("cam", unity_set_camera_transform("Main Camera", 0.0, 2.4, -7.5,
                                     8.0, 0.0, 0.0))

# 2) Fog: bounded so NEAR (<22m) is crisp, only deep bg fades.
#    Cooler dusk tint. This is 'atmosphere', not 'wall'.
s("fog", unity_set_fog(1, "Linear", -1.0, 22.0, 95.0, 0.50, 0.55, 0.62))

# 3) Sun: stronger warm key, lower angle for long shadows + mood.
s("sun.rot", unity_set_rotation("Sun_Golden", 14, -38, 0))
s("sun.props", unity_set_light_properties("Sun_Golden", 1.0, 0.83, 0.58,
                                          1.55, -1, -1, 1, 0.85))
# 4) Ambient a touch lower so the sun reads as a key (contrast = mood)
s("ambient", unity_set_ambient_light(0.34, 0.39, 0.47, 0.45, "Flat"))
# 5) Sky: cool overcast top, warm low band
s("sky", unity_set_skybox("", 0.06, 1.15, 1.0, 0.46, 0.53, 0.62,
                          0.34, 0.30, 0.25))

# 6) Density: a near cluster of pines flanking the camera->pass sightline
#    so the frame reads as 'a forest valley', not a few poles.
import math, random
random.seed(11)
for i in range(14):
    side = -1 if i % 2 == 0 else 1
    z = -4 + i * 3.2
    x = side * (2.5 + random.uniform(0, 2.2)) + random.uniform(-0.6, 0.6)
    nm = f"PineNear_{i:02d}"
    unity_create_primitive("Cylinder", nm, round(x, 2), 3.0, round(z, 2))
    unity_set_scale(nm, 0.32, 3.0, 0.32)
    unity_set_material_color(nm, 0.09, 0.12, 0.09, 1)
s("near_pines", {"ok": True, "n": 14})

unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_tuned_moody"), indent=1)[:260])
print("TUNE DONE")
