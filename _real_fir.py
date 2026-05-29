"""Phase 145: import the decimated REAL fir cluster + scatter a MODEST
count (GPU-instanced, same mesh = cheap; P143 ground-snap+colour). No
recompile (scatter_terrain_glb_trees already has the fixes). Daemon
paused. Verify visually vs the crude procedural pines.
"""
import time, json, shutil
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

FBX_SRC = "C:/Users/KITLIM~1/AppData/Local/Temp/propgen/LP_RealFir.fbx"
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
        try: return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  {cmd} fail#{k}: {str(e)[:46]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries}"}


def wait_main(tries=70, gap=7, tag="m"):
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


if not wait_main(tag="pre"): print("stalled"); raise SystemExit(0)

# import the decimated real fir FBX into the Unity project
imp = rcall("import_asset", {"src_path": FBX_SRC,
            "dst_relative": "Studio/Generated/LP_RealFir.fbx"}, t=90, retries=2)
print("import:", json.dumps(imp)[:140])
time.sleep(4)

rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)
_GM = "Assets/FantasyRPG/Generated/Materials/"
res = rcall("scatter_terrain_glb_trees", {
    "tree_count": 38, "forest_min": 0.05, "forest_max": 0.92,
    "max_slope_deg": 55, "scale_min": 1.0, "scale_max": 1.8,
    "dead_ratio": 0.0, "seed": 11, "clear_primitive_forest": True,
    "models": ["Assets/Studio/Generated/LP_RealFir.fbx"],
    "dead_models": ["Assets/Studio/Generated/LP_RealFir.fbx"],
    "trunk_material_path": _GM + "HDRP_M_WetAgedWood.mat",
    "foliage_material_path": _GM + "HDRP_M_BlackPineNeedles.mat",
    "gpu_instancing": True,
}, t=240, retries=2)
print("SCATTER:", json.dumps(res)[:340])
rcall("save_scene", {}, t=90)

d = rcall("get_object_details", {"name": "Tree_003"}, t=20)
tx = ty = tz = None
if isinstance(d, dict):
    pos = d.get("position") or {}
    if isinstance(pos, dict) and "y" in pos:
        tx, ty, tz = float(pos["x"]), float(pos["y"]), float(pos["z"])
        print("Tree_003 y=%.2f (x=%.1f z=%.1f)" % (ty, tx, tz))
if tx is None: tx, ty, tz = 225.0, 57.0, 75.0
for sz, nm in [(14, "fv_realfir_close"), (60, "fv_realfir_mid")]:
    rcall("set_scene_view", {"pivot_x": tx, "pivot_y": ty + 5.0, "pivot_z": tz,
          "size": sz, "pitch": 6, "yaw": 35}, t=30, retries=2)
    time.sleep(1.4)
    print(f"{nm}:", json.dumps(studio_capture_screenshot(name=nm))[:115])
print("REAL FIR DONE placed=%s" % (res.get("placed") if isinstance(res, dict) else "?"))
