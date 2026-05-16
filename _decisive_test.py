"""Phase 112 decisive test: recompile (Flush + basemapDistance fix),
fix_terrain_hdrp_material, then a GUARANTEED close ground shot via an
explicit pivot at the hero's feet with a tiny SceneView size (camera
~12u from ground). If the moss texture shows up close -> it was the
stale-basemap/distance issue (now fixed). If still pale up close ->
the layer/material binding itself is broken (different fix needed).
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
            print(f"  {cmd} fail#{k}: {str(e)[:48]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries}"}


def wait_main(tries=110, gap=7, tag="m"):
    ok = 0
    for i in range(tries):
        if i % 3 == 0: focus_unity_window()
        fresh()
        t0 = time.time()
        try:
            r = U.call("list_root_objects", {}, timeout=22)
            if isinstance(r, dict) and r.get("ok") and time.time()-t0 < 6.0:
                ok += 1; print(f"[{tag}] ok x{ok}")
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
if not wait_main(tries=120, tag="post"): print("stalled post"); raise SystemExit(0)

fix = rcall("fix_terrain_hdrp_material", {"terrain_name": "WorldTerrain"}, t=60, retries=2)
print("FIX:", json.dumps(fix)[:300])

# hero position -> explicit close pivot at the ground
info = rcall("get_object_details", {"name": "SK_Hero"}, t=20)
hx, hy, hz = 225.0, 57.0, 75.0
if isinstance(info, dict):
    pos = info.get("position") or {}
    if isinstance(pos, dict) and "x" in pos:
        hx, hy, hz = float(pos["x"]), float(pos["y"]), float(pos["z"])
print("hero at", round(hx,1), round(hy,1), round(hz,1))

# TRUE close-up: explicit pivot at hero feet, tiny size -> camera ~12u out
rcall("set_scene_view", {"pivot_x": hx, "pivot_y": hy + 1.0,
      "pivot_z": hz, "size": 9, "pitch": 4, "yaw": 35}, t=30, retries=2)
time.sleep(1.4)
print("CLOSE:", json.dumps(studio_capture_screenshot(name="fv_groundtruth_close"))[:120])

# medium
rcall("set_scene_view", {"pivot_x": hx, "pivot_y": hy,
      "pivot_z": hz, "size": 45, "pitch": 10, "yaw": 35}, t=30, retries=2)
time.sleep(1.4)
print("MED:", json.dumps(studio_capture_screenshot(name="fv_groundtruth_med"))[:120])
print("DECISIVE DONE fix_ok=%s" % (isinstance(fix, dict) and fix.get("ok")))
