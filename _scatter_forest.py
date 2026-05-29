"""Phase 92 apply: wait recompile -> ensure a camera -> scatter sparse
procedural forest on the real-world terrain (mid-elevation band only)
-> aerial screenshot. User watches live in the open Editor.
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
        u.call("scatter_terrain_trees", {"tree_count": 1})  # probe new handler
        print(f"[{att}] Phase 92 handler live")
        break
    except Exception as e:
        if "Unknown method" in str(e):
            print(f"[{att}] waiting recompile"); time.sleep(8); u = None
        else:
            print(f"[{att}] {str(e)[:90]}"); time.sleep(6); u = None
if u is None:
    print("RECOMPILE not ready — focus Unity, rerun."); raise SystemExit(1)

from unitytools.tools.unity_tools import unity_open_scene, unity_save_scene
from unitytools.studio.tools import studio_capture_screenshot

unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")

# Ensure a camera exists (clear_scene history removed it before)
roots = u.call("list_root_objects", {})
names = [r["name"] for r in roots.get("roots", [])] if isinstance(roots, dict) else []
print("roots:", names)
if not any(n == "Main Camera" for n in names):
    u.call("create_empty", {"name": "Main Camera"})
    u.call("add_component", {"name": "Main Camera", "type": "Camera"})
    try: u.call("set_tag", {"name": "Main Camera", "tag": "MainCamera"})
    except Exception: pass
    print("camera created")

# Scatter the sparse forest (real terrain, mid band, HDRP-safe)
sc = u.call("scatter_terrain_trees", {
    "tree_count": 260, "forest_min": 0.16, "forest_max": 0.52,
    "max_slope_deg": 33, "scale_min": 9, "scale_max": 17, "seed": 7,
})
print("SCATTER:", json.dumps(sc)[:260] if isinstance(sc, dict) else str(sc)[:260])

# HDRP exposure + aerial cam over the 16km terrain
u.call("setup_hdrp_volume", {"fixed_exposure": 12.0, "fog": True, "fog_distance": 3500})
u.call("set_camera_transform", {
    "name": "Main Camera", "position_x": -4200.0, "position_y": 2400.0,
    "position_z": -4200.0, "rotation_x": 26.0, "rotation_y": 45.0, "rotation_z": 0.0,
})
unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_forest_scatter"), indent=1)[:200])
print("SCATTER DONE")
