"""Phase 93 apply: wait recompile -> repaint terrain biomes by the
terrain's OWN relief percentile (green-dominant, snow only top peaks).
No elevation re-fetch. User watches live in the open Editor.
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
for att in range(10):
    u = fresh()
    if u is None:
        print(f"[{att}] recompiling..."); time.sleep(8); continue
    try:
        u.call("repaint_terrain_biomes", {"plains_to": 0.30})  # probe
        print(f"[{att}] Phase 93 handler live")
        break
    except Exception as e:
        if "Unknown method" in str(e):
            print(f"[{att}] waiting recompile"); time.sleep(8); u = None
        else:
            print(f"[{att}] {str(e)[:90]}"); time.sleep(6); u = None
if u is None:
    print("RECOMPILE not ready — focus Unity, rerun."); raise SystemExit(1)

from unitytools.tools.unity_tools import unity_open_scene, unity_save_scene
unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")

# Green-dominant: lowest 32% plains, 32-66% forest (the bulk/playable),
# 66-90% rock, only top 10% snow. Rich believable colours.
r = u.call("repaint_terrain_biomes", {
    "plains_to": 0.32, "forest_to": 0.66, "rock_to": 0.90,
    "plains_color": [0.30, 0.45, 0.20],
    "forest_color": [0.13, 0.27, 0.13],
    "rock_color":   [0.40, 0.39, 0.36],
    "snow_color":   [0.90, 0.92, 0.95],
})
print("REPAINT:", json.dumps(r)[:300] if isinstance(r, dict) else str(r)[:300])

# keep the darker exposure from the prior step
u.call("setup_hdrp_volume", {"fixed_exposure": 14.0, "fog": True, "fog_distance": 3500})
unity_save_scene()
print("REPAINT DONE — user: re-check Scene view (green valleys/forest, white only peaks?)")
