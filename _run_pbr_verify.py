"""Phase 107 + QA: bridge is ALREADY compiled with set_scene_view +
apply_terrain_pbr_layers (verified live). No recompile/import_asset
here -> no domain-reload storm. Just: paint real PBR ground, then
deterministic SceneView close-up + wide screenshots.
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
c, b, U = _bootstrap(); U.connect(timeout=8.0)
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
from unitytools.studio.tools import studio_capture_screenshot


def call(cmd, p, t=180):
    try:
        return U.call(cmd, p, timeout=t)
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


# quick idle confirm (no recompile expected)
t0 = time.time(); U.call("ping", {}, timeout=8)
print("ping %.2fs" % (time.time() - t0))

print("open:", json.dumps(call("open_scene",
      {"path": "Assets/Scenes/ForgottenValley_VS.unity"}))[:110])

pbr = call("apply_terrain_pbr_layers", {
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
}, t=240)
print("PBR LAYERS:", json.dumps(pbr)[:460])
call("save_scene", {})

# deterministic close-up on a real GLB tree
sv1 = call("set_scene_view", {"target": "Tree_010", "size": 18,
                              "pitch": 8, "yaw": 35}, t=30)
print("sv tree:", json.dumps(sv1)[:200])
time.sleep(1.0)
print("shot1:", json.dumps(studio_capture_screenshot(name="fv_tree_pbr_closeup"))[:150])

# mid view of a tree stand + ground
sv2 = call("set_scene_view", {"target": "WorldForestGLB", "size": 120,
                              "pitch": 14, "yaw": 38}, t=30)
print("sv forest:", json.dumps(sv2)[:200])
time.sleep(1.0)
print("shot2:", json.dumps(studio_capture_screenshot(name="fv_forest_pbr_mid"))[:150])

# wide vista of the slice
sv3 = call("set_scene_view", {"target": "WorldTerrain", "size": 520,
                              "pitch": 24, "yaw": 40}, t=30)
print("sv wide:", json.dumps(sv3)[:200])
time.sleep(1.0)
print("shot3:", json.dumps(studio_capture_screenshot(name="fv_slice_pbr_wide"))[:150])
print("PBR+VERIFY DONE pbr_ok=%s" % (isinstance(pbr, dict) and pbr.get("ok")))
