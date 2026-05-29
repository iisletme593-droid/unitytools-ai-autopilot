"""Phase 154: handle the user's Tree1 download GENUINELY. Recompile
(procedural pine now overlays the REAL conifer needle-sprig alpha
cards + bark texture harvested from Tree1ByTyroSmith), reopen
ForgottenValley_VS, rescatter the forest, CLOSE-UP screenshots so the
real foliage is visible. Resilient-retry absorbs daemon overlap.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
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


def rcall(cmd, p, t=120, retries=3):
    for k in range(retries):
        try:
            return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  {cmd} fail#{k}: {str(e)[:46]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries}"}


def wait_main(tries=130, gap=7, tag="m"):
    ok = 0
    for i in range(tries):
        if i % 3 == 0: focus_unity_window()
        fresh()
        t0 = time.time()
        try:
            r = U.call("list_root_objects", {}, timeout=22)
            if isinstance(r, dict) and r.get("ok") and time.time()-t0 < 6.0:
                ok += 1
                if ok >= 2: return True
            else: ok = 0
        except Exception as e:
            ok = 0; print(f"[{tag}] busy#{i}: {str(e)[:42]}")
        time.sleep(gap)
    return False


if not wait_main(tag="pre"): print("stalled pre"); raise SystemExit(0)
print("recompile:", json.dumps(rcall("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs"}, t=60, retries=2))[:110])
time.sleep(10)
if not wait_main(tries=130, tag="post"): print("stalled post"); raise SystemExit(0)

rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)
fr = rcall("scatter_terrain_trees", {"tree_count": 150, "forest_min": 0.05,
           "forest_max": 0.92, "max_slope_deg": 55, "scale_min": 6,
           "scale_max": 13, "seed": 11}, t=180)
print("FOREST:", json.dumps(fr, ensure_ascii=False)[:200])
rcall("save_scene", {}, t=90)

d = rcall("get_object_details", {"name": "Pine_010"}, t=20)
pos = (d.get("position") or {}) if isinstance(d, dict) else {}
gx, gy, gz = float(pos.get("x", 225)), float(pos.get("y", 60)), float(pos.get("z", 75))
print("Pine_010 y=%.2f" % gy)
for sz, nm in [(9, "fv_realconifer_tight"), (26, "fv_realconifer_close"),
               (95, "fv_realconifer_mid")]:
    rcall("set_scene_view", {"pivot_x": gx, "pivot_y": gy + 6.0, "pivot_z": gz,
          "size": sz, "pitch": 6, "yaw": 35}, t=30, retries=2)
    time.sleep(1.4)
    print(f"{nm}:", json.dumps(studio_capture_screenshot(name=nm))[:110])
print("REAL-CONIFER DONE placed=%s" % (
    fr.get("placed") if isinstance(fr, dict) else fr))
