"""Phase 106: verify the real GLB trees at human scale. Put the camera
near a forest-band tree at eye height and look across the stand, so we
can actually judge whether they read as real trees (not white blobs).
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools)
from pathlib import Path

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap(); U.connect(timeout=8.0)
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))


def call(cmd, p, t=60):
    try:
        return U.call(cmd, p, timeout=t)
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


# idle check
for _ in range(20):
    t0 = time.time()
    try:
        U.call("ping", {}, timeout=6)
        if time.time() - t0 < 1.5:
            break
    except Exception:
        try:
            U.connect(timeout=5.0)
        except Exception:
            pass
    time.sleep(4)

call("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"})

# Find a real tree to stand next to. List root objects, locate the
# WorldForestGLB, then ask for the first child's world position.
roots = call("list_root_objects", {})
print("roots:", json.dumps(roots)[:400])

# Query a few specific tree instances; pick one with a sensible position
px, py, pz = 0.0, 60.0, 0.0
for nm in ("Tree_005", "Tree_010", "Tree_000", "Tree_020", "DeadTree_000"):
    tree = call("get_object_details", {"name": nm})
    print(nm, ":", json.dumps(tree)[:200])
    if isinstance(tree, dict):
        pos = tree.get("position") or {}
        if isinstance(pos, dict) and "y" in pos:
            px = float(pos.get("x", 0.0)); py = float(pos.get("y", 60.0)); pz = float(pos.get("z", 0.0))
            break

# Stand 18m back, 2m up, look slightly up at the canopy
call("set_camera_transform", {
    "name": "Main Camera",
    "position_x": px - 18.0, "position_y": py + 4.0, "position_z": pz - 18.0,
    "rotation_x": 6.0, "rotation_y": 45.0, "rotation_z": 0.0,
})
from unitytools.studio.tools import studio_capture_screenshot
shot = studio_capture_screenshot(name="fv_trees_closeup")
print("closeup:", json.dumps(shot)[:170])
print("VERIFY DONE near", round(px, 1), round(py, 1), round(pz, 1))
