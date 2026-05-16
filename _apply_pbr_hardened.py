"""Hardened Stage 2 + QA. apply_terrain_pbr_layers + set_scene_view are
already compiled & live, so NO recompile/import_asset here (avoids the
domain-reload storm). Key robustness:
  - probe MAIN-THREAD readiness with a real op (list_root_objects),
    not just ping (ping answers on the bridge thread even when the
    Unity main thread is stalled/unfocused)
  - fresh disconnect()+connect() each retry (unity.py now nulls the
    socket on WinError 10053 / OSError, so reconnect actually works)
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools)
from pathlib import Path

TX = "Assets/FantasyRPG/Textures"
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
from unitytools.studio.tools import studio_capture_screenshot


def fresh_connect(timeout=8.0):
    try:
        U.disconnect()
    except Exception:
        pass
    try:
        return U.connect(timeout=timeout)
    except Exception:
        return False


def robust_call(cmd, p, t=120, retries=3):
    for k in range(retries):
        try:
            return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  call {cmd} fail#{k}: {str(e)[:60]}")
            fresh_connect()
            time.sleep(3)
    return {"ok": False, "error": f"{cmd} failed after {retries} tries"}


def wait_main_thread(tries=70, gap=7):
    """Real main-thread op must return quickly (not just ping)."""
    from unitytools.bridges.unity import focus_unity_window
    ok = 0
    for i in range(tries):
        if i % 3 == 0:
            focus_unity_window()
        fresh_connect()
        t0 = time.time()
        try:
            r = U.call("list_root_objects", {}, timeout=22)
            dt = time.time() - t0
            if isinstance(r, dict) and r.get("ok") and dt < 6.0:
                ok += 1
                print(f"[main] responsive ({dt:.2f}s) x{ok}")
                if ok >= 2:
                    return True
            else:
                ok = 0
                print(f"[main] slow/bad ({dt:.2f}s) #{i}")
        except Exception as e:
            ok = 0
            print(f"[main] busy #{i}: {str(e)[:55]}")
        time.sleep(gap)
    return False


print("waiting for Unity main thread to be free (cold boot can take a while)...")
if not wait_main_thread(tries=130, gap=7):  # ~15 min: covers a cold Unity boot
    print("MAIN THREAD STILL STALLED after ~15min; aborting cleanly")
    raise SystemExit(0)

print("open:", json.dumps(robust_call("open_scene",
      {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120))[:110])

pbr = robust_call("apply_terrain_pbr_layers", {
    "cutoffs": [0.34, 0.62, 0.88],
    "layers": [
        {"name": "Moss", "tile": 10,
         "diffuse": f"{TX}/Ground/Ground037/Ground037_2K-JPG_Color.jpg",
         "normal":  f"{TX}/Ground/Ground037/Ground037_2K-JPG_NormalGL.jpg"},
        {"name": "WetEarth", "tile": 11,
         "diffuse": f"{TX}/Ground/Ground103/Ground103_2K-JPG_Color.jpg",
         "normal":  f"{TX}/Ground/Ground103/Ground103_2K-JPG_NormalGL.jpg"},
        {"name": "MossRock", "tile": 13,
         "diffuse": f"{TX}/Rock/Rock063/Rock063_2K-JPG_Color.jpg",
         "normal":  f"{TX}/Rock/Rock063/Rock063_2K-JPG_NormalGL.jpg"},
        {"name": "DarkRock", "tile": 15,
         "diffuse": f"{TX}/Rock/Rock058/Rock058_2K-JPG_Color.jpg",
         "normal":  f"{TX}/Rock/Rock058/Rock058_2K-JPG_NormalGL.jpg"},
    ],
}, t=240, retries=2)
print("PBR LAYERS:", json.dumps(pbr)[:460])
robust_call("save_scene", {}, t=90)

for tgt, sz, pit, yw, nm in [
    ("Tree_010", 18, 8, 35, "fv_tree_pbr_closeup"),
    ("WorldForestGLB", 110, 14, 38, "fv_forest_pbr_mid"),
    ("WorldTerrain", 520, 24, 40, "fv_slice_pbr_wide"),
]:
    sv = robust_call("set_scene_view",
                      {"target": tgt, "size": sz, "pitch": pit, "yaw": yw},
                      t=30, retries=2)
    print(f"sv {tgt}:", json.dumps(sv)[:140])
    time.sleep(1.2)
    print("shot:", json.dumps(studio_capture_screenshot(name=nm))[:140])

print("HARDENED PBR+QA DONE pbr_ok=%s" % (isinstance(pbr, dict) and pbr.get("ok")))
