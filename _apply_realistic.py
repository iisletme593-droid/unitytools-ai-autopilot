"""Apply the realistic layer that the stale plugin rejected before:
ambient, skybox, hearth emissive, ground PBR, camera framing.
Geometry + sun + fog already persist in ForgottenValley_VS.
"""
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
    unity_set_fog, unity_set_ambient_light, unity_set_skybox,
    unity_set_material_pbr, unity_set_camera_transform, unity_save_scene,
)
from unitytools.studio.tools import studio_capture_screenshot
import json

def s(label, r):
    ok = isinstance(r, dict) and r.get("ok", True)
    print(("OK  " if ok else "ERR ") + label + ("" if ok else f"  {r}"))

# Re-assert fog (idempotent) + the previously-rejected realistic layer
s("fog", unity_set_fog(1, "Linear", -1.0, 15.0, 72.0, 0.55, 0.60, 0.66))
s("ambient", unity_set_ambient_light(0.42, 0.47, 0.55, 0.55, "Flat"))
s("sky", unity_set_skybox("", 0.05, 1.1, 1.0, 0.50, 0.56, 0.64,
                          0.30, 0.27, 0.24))
s("hearth.emis", unity_set_material_pbr("Hearth_Base", emission_enabled=1,
    emission_r=1.0, emission_g=0.45, emission_b=0.12, emission_intensity=2.4))
s("ground.pbr", unity_set_material_pbr("Ground", metallic=0.0, smoothness=0.12))
# Third-person framing: behind+above hearth, slight downward, see the pass
s("cam", unity_set_camera_transform("Main Camera", 0.0, 6.5, -14.0,
                                     17.0, 0.0, 0.0))
s("save", unity_save_scene())
print(json.dumps(studio_capture_screenshot(name="fv_realistic_02"), indent=1)[:300])
