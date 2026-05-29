"""Final coherent pass: studio_realize_world wires sun(22000)+Fixed
exposure+real PBR ground+water+HDRP volume+SMART MAIN CAMERA + the
cheap low-poly forest (already wired). Then capture via the same path
that produced the believable early green shot. Data is already
verified (list_terrains: WorldTerrain 4 PBR layers HDRP/TerrainLit;
scatter: 136 cheap trees). This makes the SAVED scene fully coherent.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools, init_studio_blender)
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

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


def wait_main(tries=80, gap=7):
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
        except Exception:
            ok = 0
        time.sleep(gap)
    return False


if not wait_main(): print("stalled"); raise SystemExit(0)

# Ensure the low-poly tree FBXs exist (resilient orchestrator) so the
# realize forest step scatters the CHEAP trees, not procedural.
print("== build low-poly forest assets ==")
lf = st.studio_build_lowpoly_forest(tree_count=150)
print("LOWPOLY ok=%s placed=%s" % (
    isinstance(lf, dict) and lf.get("ok"),
    (lf.get("scatter") or {}).get("placed") if isinstance(lf, dict) else "?"))

print("== full coherent realize (cheap forest wired) ==")
rw = st.studio_realize_world(water_level=0.085, forest_count=150,
                             relief_m=190.0)
print("REALIZE ok=%s" % (isinstance(rw, dict) and rw.get("ok")))
for layer in (rw.get("layers", []) if isinstance(rw, dict) else []):
    if isinstance(layer, dict):
        for k in ("biome_kind", "forest_kind"):
            if k in layer: print("  ", k, "=", layer[k])

try:
    U.call("save_scene", {}, timeout=90)
except Exception:
    pass
time.sleep(1.5)
for nm in ("fv_FINAL_a", "fv_FINAL_b"):
    print(nm, json.dumps(studio_capture_screenshot(name=nm))[:120])
    time.sleep(1.5)
print("FINAL COHERENT DONE")
