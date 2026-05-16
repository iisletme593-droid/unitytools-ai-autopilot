"""Hypothesis: the 'pale ground' on lit faces is OVEREXPOSURE (Fixed
exposure 13 + 22000lx sun blows out real PBR albedo; shadowed faces
show true texture). Sweep exposure low->high, capture each. No
recompile. If a lower exposure reveals the moss/earth -> solved.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
from unitytools.studio.tools import studio_capture_screenshot


def fresh(t=8.0):
    try: U.disconnect()
    except Exception: pass
    try: return U.connect(timeout=t)
    except Exception: return False


def rcall(cmd, p, t=60, retries=3):
    for k in range(retries):
        try:
            return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  {cmd} fail#{k}: {str(e)[:44]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries}"}


focus_unity_window(); time.sleep(1); fresh()
rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)
# frame a fixed near-ground viewpoint over the moss band
rcall("set_scene_view", {"target": "WorldForestGLB", "size": 80,
                         "pitch": 12, "yaw": 35}, t=30, retries=2)

for ev in (14.5, 15.5, 16.5, 17.5, 19.0):
    r = rcall("setup_hdrp_volume", {"exposure_mode": "Fixed",
              "fixed_exposure": ev, "fog": True, "fog_distance": 2400},
              t=60, retries=2)
    time.sleep(1.4)
    nm = f"fv_exp_{str(ev).replace('.','p')}"
    shot = studio_capture_screenshot(name=nm)
    print(f"EV={ev}", "vol_ok=%s" % (isinstance(r, dict) and r.get("ok")),
          "shot=%s" % (isinstance(shot, dict) and shot.get("ok")))

# also try Automatic exposure (HDRP auto-adapts)
r = rcall("setup_hdrp_volume", {"exposure_mode": "Automatic",
          "fog": True, "fog_distance": 2400}, t=60, retries=2)
time.sleep(1.6)
print("AUTO", json.dumps(studio_capture_screenshot(name="fv_exp_auto"))[:110])
print("EXPOSURE SWEEP DONE")
