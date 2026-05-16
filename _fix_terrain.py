"""Make the already-built real-world terrain visible: assign HDRP
terrain material + clear old broken-GLB clutter. No elevation re-fetch.
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
for att in range(10):
    u = fresh()
    if u is None:
        print(f"[{att}] recompiling..."); time.sleep(8); continue
    try:
        u.call("fix_terrain_material", {"clear_clutter": True})
        print(f"[{att}] handler live")
        break
    except Exception as e:
        if "Unknown method" in str(e):
            print(f"[{att}] old build; waiting recompile"); time.sleep(8); u = None
        else:
            print(f"[{att}] {str(e)[:90]}"); time.sleep(6); u = None
if u is None:
    print("RECOMPILE not ready — focus Unity, rerun."); raise SystemExit(1)

from unitytools.tools.unity_tools import unity_open_scene, unity_set_camera_transform, unity_save_scene
from unitytools.studio.tools import studio_capture_screenshot

unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")
r = u.call("fix_terrain_material", {"clear_clutter": True})
print("FIX:", json.dumps(r)[:300] if isinstance(r, dict) else str(r)[:300])

# Re-assert exposure (HDRP) so the terrain reads, and aerial framing
u.call("setup_hdrp_volume", {"fixed_exposure": 12.0, "fog": True, "fog_distance": 1200})
roots = u.call("list_root_objects", {})
print("roots now:", [x["name"] for x in roots.get("roots", [])] if isinstance(roots, dict) else roots)

# 16km terrain, relief ~1168m. Aerial 3/4 from a corner.
unity_set_camera_transform("Main Camera", -6000.0, 2800.0, -6000.0, 32.0, 45.0, 0.0)
unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_terrain_visible"), indent=1)[:200])
print("TERRAIN FIX DONE")
