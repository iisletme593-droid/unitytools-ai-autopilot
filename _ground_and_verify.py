"""Phase 106-107: self-recompile (import_asset trick) so set_scene_view +
apply_terrain_pbr_layers go live, then:
  - paint terrain with real 2K PBR ground/rock (art-bible palette)
  - SceneView close-up on a real GLB tree   -> screenshot
  - SceneView wide vista of the slice       -> screenshot
No manual Ctrl+R; idle-wait pattern throughout.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools)
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
TX = "Assets/FantasyRPG/Textures"

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap(); U.connect(timeout=8.0)
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
from unitytools.studio.tools import studio_capture_screenshot


def call(cmd, p, t=120):
    try:
        return U.call(cmd, p, timeout=t)
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


def wait_idle(tag, tries=60, gap=6):
    idle = 0
    for attempt in range(tries):
        t0 = time.time()
        try:
            U.call("ping", {}, timeout=8)
            if time.time() - t0 < 1.5:
                idle += 1
                if idle >= 3:
                    print(f"[{tag}] idle"); return True
            else:
                idle = 0
        except Exception as e:
            idle = 0
            print(f"[{tag}] busy #{attempt}: {str(e)[:45]}")
            try: U.connect(timeout=5.0)
            except Exception: pass
        time.sleep(gap)
    return False


wait_idle("pre", tries=20)
print("force-recompile:", json.dumps(call("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs",
}, t=60))[:140])
time.sleep(8)
if not wait_idle("recompile", tries=60, gap=6):
    raise SystemExit("Unity did not settle after recompile")

print("open:", json.dumps(call("open_scene",
      {"path": "Assets/Scenes/ForgottenValley_VS.unity"}))[:110])

# --- Stage 2: real PBR ground/rock layers (Briar Hollow palette) ---
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
}, t=180)
print("PBR LAYERS:", json.dumps(pbr)[:420])

call("save_scene", {})

# --- close-up on a real GLB tree via the new SceneView control ---
sv1 = call("set_scene_view", {"target": "Tree_010", "size": 16,
                              "pitch": 8, "yaw": 35})
print("sv tree:", json.dumps(sv1)[:200])
time.sleep(1.0)
s1 = studio_capture_screenshot(name="fv_tree_pbr_closeup")
print("shot1:", json.dumps(s1)[:150])

# --- wide vista of the whole slice ---
sv2 = call("set_scene_view", {"target": "WorldTerrain", "size": 520,
                              "pitch": 26, "yaw": 40})
print("sv wide:", json.dumps(sv2)[:200])
time.sleep(1.0)
s2 = studio_capture_screenshot(name="fv_slice_pbr_wide")
print("shot2:", json.dumps(s2)[:150])
print("GROUND+VERIFY DONE pbr_ok=%s" % (isinstance(pbr, dict) and pbr.get("ok")))
