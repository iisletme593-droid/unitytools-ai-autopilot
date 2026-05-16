"""Phase 95 apply: the intelligent playable pass.
recompile -> make_terrain_playable (1.2km footprint, hero on a valley
spawn, third-person cam) -> re-scatter forest on the NEW small terrain
-> Automatic adaptive exposure -> screenshot.
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
for att in range(12):
    u = fresh()
    if u is None:
        print(f"[{att}] recompiling..."); time.sleep(8); continue
    try:
        u.call("make_terrain_playable", {"footprint_m": 1200})
        print(f"[{att}] Phase 95 handler live")
        break
    except Exception as e:
        if "Unknown method" in str(e):
            print(f"[{att}] waiting recompile"); time.sleep(8); u = None
        else:
            print(f"[{att}] {str(e)[:90]}"); time.sleep(6); u = None
if u is None:
    print("RECOMPILE not ready - focus Unity, rerun."); raise SystemExit(1)

from unitytools.tools.unity_tools import unity_open_scene, unity_save_scene
from unitytools.studio.tools import studio_capture_screenshot
unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")

# 1) Rescale to playable + spawn hero on a valley meadow + 3rd-person cam
mp = u.call("make_terrain_playable", {
    "footprint_m": 1200, "relief_scale": 0.16,
    "character": "SK_Hero", "character_scale": 1.0,
})
print("PLAYABLE:", json.dumps(mp)[:320] if isinstance(mp, dict) else str(mp)[:320])

# 2) Re-paint biomes for the (now small) terrain — green dominant
u.call("repaint_terrain_biomes", {
    "plains_to": 0.34, "forest_to": 0.66, "rock_to": 0.90,
    "plains_color": [0.30, 0.45, 0.20], "forest_color": [0.13, 0.27, 0.13],
    "rock_color": [0.40, 0.39, 0.36], "snow_color": [0.90, 0.92, 0.95],
})

# 3) Old WorldForest was at 16km coords -> re-scatter on the 1.2km terrain
sc = u.call("scatter_terrain_trees", {
    "tree_count": 240, "forest_min": 0.16, "forest_max": 0.55,
    "max_slope_deg": 34, "scale_min": 6, "scale_max": 12, "seed": 5,
})
print("FOREST:", json.dumps(sc)[:200] if isinstance(sc, dict) else str(sc)[:200])

# 4) Adaptive exposure — never pure black/white again
u.call("setup_hdrp_volume", {"exposure_mode": "Automatic", "fog": True,
                              "fog_distance": 900})
unity_save_scene()
shot = studio_capture_screenshot(name="fv_playable")
print("SHOT:", json.dumps(shot)[:170] if isinstance(shot, dict) else str(shot)[:170])
print("PLAYABLE PASS DONE")
