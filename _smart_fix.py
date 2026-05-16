"""Phase 94 apply: wait recompile -> HDRP Automatic (adaptive) exposure
+ smart auto-framing camera with world-scaled clip planes + HDRP cam
data. Fixes pitch-black AND zoom-vanish. Then try a screenshot (the
HDRP cam data may finally make capture work).
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]

def fresh():
    c, b, u = _bootstrap()
    if not u.connect(timeout=3.0):
        return None
    init_studio_unity(u); ut._UNITY = u
    init_studio_tools(StudioState(P))
    return u

u = None
for att in range(12):
    u = fresh()
    if u is None:
        print(f"[{att}] recompiling..."); time.sleep(8); continue
    try:
        u.call("setup_smart_camera", {"target": "WorldTerrain"})  # probe
        print(f"[{att}] Phase 94 handlers live")
        break
    except Exception as e:
        if "Unknown method" in str(e):
            print(f"[{att}] waiting recompile"); time.sleep(8); u = None
        else:
            print(f"[{att}] {str(e)[:90]}"); time.sleep(6); u = None
if u is None:
    print("RECOMPILE not ready - focus Unity, rerun."); raise SystemExit(1)

from unitytools.tools.unity_tools import unity_open_scene, unity_save_scene
from unitytools.studio.tools import studio_capture_screenshot
unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")

# 1) Adaptive exposure — never pure black/white again (the smart fix)
ev = u.call("setup_hdrp_volume", {"exposure_mode": "Automatic",
                                  "fog": True, "fog_distance": 3500})
print("EXPOSURE:", json.dumps(ev)[:260] if isinstance(ev, dict) else str(ev)[:260])

# 2) Smart camera: auto-frame terrain, clip planes scaled to 16km world
cam = u.call("setup_smart_camera", {"target": "WorldTerrain",
                                    "pitch": 26, "yaw": 35, "distance_factor": 0.6})
print("CAMERA:", json.dumps(cam)[:300] if isinstance(cam, dict) else str(cam)[:300])

unity_save_scene()
shot = studio_capture_screenshot(name="fv_smart")
print("SHOT:", json.dumps(shot)[:200] if isinstance(shot, dict) else str(shot)[:200])
print("SMART FIX DONE")
