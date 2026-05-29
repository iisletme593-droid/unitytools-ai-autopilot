"""Fix: trees sank under terrain + were colorless. Recompile
(scatter_terrain_glb_trees now: pivot-agnostic ground-snap by renderer
bounds + guaranteed coloured HDRP trunk/foliage materials), rebuild the
low-poly forest, then a close-up at a tree to verify ON the surface +
coloured. Daemon paused.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools, init_studio_blender)
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
try: init_studio_blender(b)
except Exception as e: print("blender warn:", e)
import unitytools.studio.tools as st
from unitytools.studio.tools import studio_capture_screenshot


def fresh(t=8.0):
    try: U.disconnect()
    except Exception: pass
    try: return U.connect(timeout=t)
    except Exception: return False


def rcall(cmd, p, t=120, retries=3):
    for k in range(retries):
        try: return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  {cmd} fail#{k}: {str(e)[:46]}")
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
if not wait_main(tries=120, tag="post"): print("stalled post"); raise SystemExit(0)

rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)
lf = st.studio_build_lowpoly_forest(tree_count=150)
sc = lf.get("scatter") if isinstance(lf, dict) else {}
print("FOREST ok=%s placed=%s note=%s" % (
    isinstance(lf, dict) and lf.get("ok"),
    sc.get("placed") if isinstance(sc, dict) else "?",
    sc.get("note") if isinstance(sc, dict) else "?"))

# verify: a tree's Y vs terrain, + close-up
d = rcall("get_object_details", {"name": "Tree_005"}, t=20)
tx = ty = tz = None
if isinstance(d, dict):
    pos = d.get("position") or {}
    if isinstance(pos, dict) and "y" in pos:
        tx, ty, tz = float(pos["x"]), float(pos["y"]), float(pos["z"])
        print("Tree_005 at y=%.2f (x=%.1f z=%.1f)" % (ty, tx, tz))
if tx is None:
    tx, ty, tz = 225.0, 57.0, 75.0
rcall("set_scene_view", {"pivot_x": tx, "pivot_y": ty + 3.0, "pivot_z": tz,
      "size": 12, "pitch": 5, "yaw": 35}, t=30, retries=2)
time.sleep(1.4)
print("closeup:", json.dumps(studio_capture_screenshot(name="fv_trees_fixed"))[:120])
rcall("set_scene_view", {"pivot_x": tx, "pivot_y": ty, "pivot_z": tz,
      "size": 55, "pitch": 12, "yaw": 35}, t=30, retries=2)
time.sleep(1.4)
print("mid:", json.dumps(studio_capture_screenshot(name="fv_trees_fixed_mid"))[:120])
print("FIX TREES DONE")
