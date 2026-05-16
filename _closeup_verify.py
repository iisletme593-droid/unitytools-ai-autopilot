"""Decisive close-up: no recompile (all compiled). Find a placed tree,
put the SceneView right next to it at small size (close camera ->
HDRP capture path is reliable, per session evidence), screenshot.
Also an eye-level shot near the hero. This shows the REAL result:
cheap low-poly forest on real PBR ground.
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


def rcall(cmd, p, t=40, retries=3):
    for k in range(retries):
        try:
            return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  {cmd} fail#{k}: {str(e)[:46]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries}"}


focus_unity_window(); time.sleep(1); fresh()
rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)

# Find a few placed trees; pick the first that resolves a position.
tx = ty = tz = None
for nm in ("Tree_000", "Tree_005", "Tree_010", "Tree_020", "Tree_050",
           "DeadTree_000", "DeadTree_005"):
    d = rcall("get_object_details", {"name": nm}, t=20)
    if isinstance(d, dict):
        pos = d.get("position") or {}
        if isinstance(pos, dict) and "x" in pos:
            tx, ty, tz = float(pos["x"]), float(pos["y"]), float(pos["z"])
            print("tree", nm, "at", round(tx, 1), round(ty, 1), round(tz, 1))
            break

if tx is None:
    # fall back to hero
    d = rcall("get_object_details", {"name": "SK_Hero"}, t=20)
    pos = d.get("position", {}) if isinstance(d, dict) else {}
    tx, ty, tz = float(pos.get("x", 225)), float(pos.get("y", 57)), float(pos.get("z", 75))
    print("fallback hero at", tx, ty, tz)

# tight close-up right beside the tree (camera ~10-14u away)
for sz, pit, yw, nm in [(7, 2, 30, "fv_done_tree"),
                        (22, 6, 40, "fv_done_cluster"),
                        (90, 14, 38, "fv_done_grove")]:
    rcall("set_scene_view", {"pivot_x": tx, "pivot_y": ty + 2.0,
          "pivot_z": tz, "size": sz, "pitch": pit, "yaw": yw}, t=30, retries=2)
    time.sleep(1.6)
    print(f"shot {nm}:", json.dumps(studio_capture_screenshot(name=nm))[:115])
print("CLOSEUP VERIFY DONE near", round(tx, 1), round(tz, 1))
