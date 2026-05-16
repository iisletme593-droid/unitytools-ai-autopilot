"""Phase 113 run: recompile (relief-aware ResolveSceneTerrain +
list_terrains + per-slot/instanced scatter), DIAGNOSE all terrains,
apply real PBR ground to the correct (relief) terrain, then build the
CHEAP Blender low-poly conifer forest (HDRP perf fix). QA close-ups.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools)
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
TX = "Assets/FantasyRPG/Textures"
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
import unitytools.studio.tools as st
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


def wait_main(tries=120, gap=7, tag="m"):
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
            ok = 0; print(f"[{tag}] busy#{i}: {str(e)[:40]}")
        time.sleep(gap)
    return False


if not wait_main(tag="pre"): print("stalled pre"); raise SystemExit(0)
print("recompile:", json.dumps(rcall("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs"}, t=60, retries=2))[:110])
time.sleep(10)
if not wait_main(tries=130, tag="post"): print("stalled post"); raise SystemExit(0)

rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)

# DIAGNOSE: list every terrain so we know the real one
lt = rcall("list_terrains", {}, t=40, retries=2)
print("TERRAINS:", json.dumps(lt)[:700])

# Apply real PBR ground to the correct (relief) terrain — no
# terrain_name, ResolveSceneTerrain now skips flat tiles.
pbr = rcall("apply_terrain_pbr_layers", {
    "cutoffs": [0.34, 0.62, 0.88],
    "layers": [
        {"name": "Moss", "tile": 9,
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
    ]}, t=240, retries=2)
print("PBR:", json.dumps(pbr)[:260])

# Cheap Blender low-poly conifer forest (HDRP perf fix)
print("== studio_build_lowpoly_forest ==")
lf = st.studio_build_lowpoly_forest(tree_count=150)
print("LOWPOLY:", json.dumps(lf)[:420])

rcall("save_scene", {}, t=90)

for tgt, sz, pit, yw, nm in [
    ("WorldForestGLB", 60, 8, 35, "fv_lp_forest"),
    ("WorldForestGLB", 150, 15, 38, "fv_lp_mid"),
    ("WorldForestGLB", 420, 24, 40, "fv_lp_wide"),
]:
    rcall("set_scene_view", {"target": tgt, "size": sz, "pitch": pit,
                             "yaw": yw}, t=30, retries=2)
    time.sleep(1.4)
    print(f"shot {nm}:", json.dumps(studio_capture_screenshot(name=nm))[:115])
print("LOWPOLY FOREST RUN DONE pbr=%s lp=%s" % (
    isinstance(pbr, dict) and pbr.get("ok"),
    isinstance(lf, dict) and lf.get("ok")))
