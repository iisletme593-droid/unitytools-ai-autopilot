"""Phase 88 verify: wait for recompile, recover scene (revert guard),
re-assert realistic layer, capture via the now URP-correct path, done.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

p = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in p.all_dirs()]

def fresh():
    c, b, u = _bootstrap()
    if not u.connect(timeout=3.0):
        return None
    init_studio_unity(u); ut._UNITY = u
    init_studio_tools(StudioState(p))
    return u

ok = False
for attempt in range(8):
    u = fresh()
    if u is None:
        print(f"[{attempt}] bridge down (recompiling?)")
        time.sleep(8); continue
    from unitytools.tools.unity_tools import unity_list_scenes
    try:
        sc = unity_list_scenes()
        act = [s for s in sc.get("scenes", []) if s.get("active")]
        active_name = act[0]["name"] if act else "?"
        print(f"[{attempt}] bridge up, active={active_name}")
        ok = True
        break
    except Exception as e:
        print(f"[{attempt}] not ready: {e}")
        time.sleep(8)

if not ok:
    print("BRIDGE NEVER CAME BACK — focus Unity so it recompiles, rerun.")
    raise SystemExit(1)

from unitytools.tools.unity_tools import (
    unity_open_scene, unity_list_scenes, unity_set_fog,
    unity_set_ambient_light, unity_set_skybox, unity_save_scene,
)
from unitytools.studio.tools import studio_capture_screenshot

# Scene-revert guard: domain reload may have reverted to Main.unity
print("recover:", json.dumps(unity_open_scene(
    "Assets/Scenes/ForgottenValley_VS.unity"))[:120])
act = [s for s in unity_list_scenes().get("scenes", []) if s.get("active")]
print("active now:", act[0]["name"] if act else "?")

# Re-assert the realistic layer (idempotent; persisted but be safe)
unity_set_fog(1, "Linear", -1.0, 15.0, 72.0, 0.55, 0.60, 0.66)
unity_set_ambient_light(0.42, 0.47, 0.55, 0.55, "Flat")
unity_set_skybox("", 0.05, 1.1, 1.0, 0.50, 0.56, 0.64, 0.30, 0.27, 0.24)
unity_save_scene()

r = studio_capture_screenshot(name="fv_urp_capture_fixed")
print(json.dumps(r, indent=1)[:300])
print("VERIFY DONE")
