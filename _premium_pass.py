"""Phase 90 apply: wait recompile -> recover scene -> READ WHOLE SCENE
(list_root_objects, no cap) -> assign project's premium HDRP materials
by root-name (trees/rocks/ground) -> re-assert HDRP exposure -> shot.
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
for att in range(9):
    u = fresh()
    if u is None:
        print(f"[{att}] recompiling..."); time.sleep(8); continue
    try:
        u.call("list_root_objects", {})  # new handler => proves recompiled
        print(f"[{att}] bridge up + Phase 90 handlers live")
        break
    except Exception as e:
        if "Unknown method" in str(e):
            print(f"[{att}] old build still loaded, waiting recompile")
        else:
            print(f"[{att}] {str(e)[:80]}")
        time.sleep(8); u = None
if u is None:
    print("BRIDGE/RECOMPILE not ready — focus Unity, rerun."); raise SystemExit(1)

from unitytools.tools.unity_tools import unity_open_scene, unity_save_scene
from unitytools.studio.tools import studio_capture_screenshot

unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")

# 1) READ THE WHOLE SCENE (user's explicit ask) — structural, no cap
roots = u.call("list_root_objects", {})
rl = roots.get("roots", []) if isinstance(roots, dict) else []
print(f"SCENE ROOTS ({roots.get('root_count') if isinstance(roots,dict) else '?'}):")
for r in rl:
    print(f"  {r['name']:<34} children={r['children']:<5} renderers={r['renderers']}")

# 2) Assign the project's PREMIUM HDRP materials by root-name match
M = "Assets/FantasyRPG/Generated/Materials/"
jobs = [
    ("Nature_Trees", M + "HDRP_M_BlackPineNeedles.mat"),
    ("Nature_Rocks", M + "HDRP_M_WetRock.mat"),
    ("UnityTools_ForestScene", M + "HDRP_M_WetForestMud.mat"),
    ("Ground", M + "HDRP_M_WetForestMud.mat"),
    ("Terrain", M + "HDRP_M_WetForestMud.mat"),
]
for needle, mat in jobs:
    r = u.call("assign_material_asset", {
        "material_path": mat, "name_contains": needle, "recurse": True,
    })
    print(f"assign {needle:<24} <- {mat.split('/')[-1]:<28} "
          f"=> {json.dumps(r)[:160] if isinstance(r,dict) else str(r)[:160]}")

# 3) Re-assert HDRP exposure volume (persisted, but be safe)
u.call("setup_hdrp_volume", {"fixed_exposure": 12.5, "fog": True,
                              "fog_distance": 300})

unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_premium_mats"), indent=1)[:220])
print("PREMIUM PASS DONE")
