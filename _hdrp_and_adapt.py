"""Phase 89 apply + scene adaptation. Wait recompile -> recover scene
-> HDRP Global Volume (the white-out fix) -> campfire + green ground
-> screenshot. All after one reinstall.
"""
import time, json, math, random
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
for att in range(9):
    u = fresh()
    if u is None:
        print(f"[{att}] bridge down (recompiling)"); time.sleep(8); continue
    try:
        u.call("ping", {})
        print(f"[{att}] bridge up")
        break
    except Exception as e:
        print(f"[{att}] not ready: {e}"); time.sleep(8); u = None
if u is None:
    print("BRIDGE NEVER CAME BACK — focus Unity, rerun."); raise SystemExit(1)

from unitytools.tools.unity_tools import (
    unity_open_scene, unity_list_scenes, unity_list_scene_objects,
    unity_set_material_color, unity_save_scene,
)
from unitytools.studio.tools import studio_capture_screenshot

# scene-revert guard
unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")
act = [s for s in unity_list_scenes().get("scenes", []) if s.get("active")]
print("active:", act[0]["name"] if act else "?")

# 1) THE white-out fix: HDRP Global Volume (new Phase 89 handler)
hv = u.call("setup_hdrp_volume", {"fixed_exposure": 12.5, "fog": True,
                                   "fog_distance": 240})
print("hdrp_volume:", json.dumps(hv)[:400] if not isinstance(hv, str) else hv[:400])

# 2) Campfire near where the hero stands (~0,0,-3). Try dedicated
#    bridge fire commands in order of preference.
fire = None
for cmd in ("campfire", "ates", "fire"):
    try:
        r = u.call(cmd, {"x": 0.0, "y": 0.0, "z": -3.0, "name": "ForgottenValley_Campfire"})
        if isinstance(r, dict) and r.get("ok"):
            fire = (cmd, r); break
    except Exception as e:
        print(f"  fire cmd {cmd} failed: {str(e)[:80]}")
print("campfire:", fire[0] if fire else "NONE", json.dumps(fire[1])[:160] if fire else "")

# 3) Green the ground / terrain
o = unity_list_scene_objects()
names = [(x if isinstance(x, str) else x.get("name")) for x in o.get("objects", [])]
greened = 0
for n in names:
    if n and any(k in n.lower() for k in ("ground", "terrain", "forestscene")):
        r = unity_set_material_color(n, 0.13, 0.30, 0.10, 1.0)
        if isinstance(r, dict) and r.get("ok"):
            greened += 1
print(f"greened {greened} ground/terrain objects (sample of {len(names)} objs)")

unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_hdrp_exposed"), indent=1)[:230])
print("HDRP+ADAPT DONE")
