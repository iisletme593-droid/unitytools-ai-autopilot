"""Phase 111: recompile (robust pattern) so fix_terrain_hdrp_material +
place_asset_on_terrain go live, then diagnose+fix the terrain HDRP
material (root cause of the pale-desert look: Shader.Find('HDRP/
TerrainLit') == null on a fresh boot -> built-in fallback), re-apply
the real PBR layers on the now-correct material, QA screenshots.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
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
            print(f"  {cmd} fail#{k}: {str(e)[:50]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries} fail"}


def wait_main(tries=90, gap=7, tag="main"):
    ok = 0
    for i in range(tries):
        if i % 3 == 0:
            focus_unity_window()
        fresh()
        t0 = time.time()
        try:
            r = U.call("list_root_objects", {}, timeout=22)
            if isinstance(r, dict) and r.get("ok") and time.time() - t0 < 6.0:
                ok += 1
                print(f"[{tag}] ok x{ok}")
                if ok >= 2: return True
            else:
                ok = 0
        except Exception as e:
            ok = 0; print(f"[{tag}] busy #{i}: {str(e)[:45]}")
        time.sleep(gap)
    return False


print("== wait main (pre) ==")
if not wait_main(tag="pre"): print("stalled pre"); raise SystemExit(0)

print("recompile:", json.dumps(rcall("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs"}, t=60, retries=2))[:130])
time.sleep(10)

print("== wait main (post-recompile) ==")
if not wait_main(tries=120, tag="post"): print("stalled post"); raise SystemExit(0)

# diagnose + fix the terrain material
fix = rcall("fix_terrain_hdrp_material", {}, t=60, retries=2)
print("FIX TERRAIN:", json.dumps(fix)[:400])

# re-apply real PBR layers on the now-correct HDRP terrain material
pbr = rcall("apply_terrain_pbr_layers", {
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
    ]}, t=240, retries=2)
print("PBR:", json.dumps(pbr)[:300])
rcall("save_scene", {}, t=90)

for tgt, sz, pit, yw, nm in [
    ("WorldForestGLB", 70, 9, 35, "fv_fix_forest"),
    ("WorldForestGLB", 170, 16, 38, "fv_fix_mid"),
    ("WorldTerrain", 480, 26, 40, "fv_fix_wide"),
]:
    rcall("set_scene_view", {"target": tgt, "size": sz, "pitch": pit,
                             "yaw": yw}, t=30, retries=2)
    time.sleep(1.3)
    print(f"shot {nm}:", json.dumps(studio_capture_screenshot(name=nm))[:120])
print("FIX+QA DONE fix=%s pbr=%s" % (
    isinstance(fix, dict) and fix.get("ok"),
    isinstance(pbr, dict) and pbr.get("ok")))
