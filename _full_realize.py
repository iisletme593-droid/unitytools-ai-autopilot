"""Unity is responsive again. The earlier pale-desert + white-trees
result was because only the ground layer got swapped after the Unity
restart, without the coherent HDRP lighting/material pipeline. Re-run
the FULL studio_realize_world (Phase 106-107 upgraded): ensure sun
22000lux -> real PBR ground -> water -> real GLB trees -> Fixed
exposure 13 + fog -> HDRP volume. Then deterministic SceneView QA.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools)
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
import unitytools.studio.tools as st
from unitytools.studio.tools import studio_capture_screenshot


def fresh_connect(t=8.0):
    try: U.disconnect()
    except Exception: pass
    try: return U.connect(timeout=t)
    except Exception: return False


def robust_call(cmd, p, t=120, retries=3):
    for k in range(retries):
        try:
            return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  {cmd} fail#{k}: {str(e)[:55]}")
            focus_unity_window(); fresh_connect(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} failed x{retries}"}


def wait_main(tries=60, gap=7):
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
                print(f"[main] ok ({dt:.2f}s) x{ok}")
                if ok >= 2: return True
            else:
                ok = 0; print(f"[main] slow ({dt:.2f}s) #{i}")
        except Exception as e:
            ok = 0; print(f"[main] busy #{i}: {str(e)[:50]}")
        time.sleep(gap)
    return False


print("== wait main thread ==")
if not wait_main():
    print("STALLED; abort clean"); raise SystemExit(0)

print("== full studio_realize_world (coherent HDRP pipeline) ==")
rw = st.studio_realize_world(water_level=0.085, forest_count=240,
                             relief_m=190.0)
ok = isinstance(rw, dict) and rw.get("ok")
print("REALIZE ok=%s" % ok)
# print which kinds the realizer used (real PBR? real GLB trees?)
for layer in (rw.get("layers", []) if isinstance(rw, dict) else []):
    if isinstance(layer, dict):
        for key in ("biome_kind", "forest_kind"):
            if key in layer:
                print("  ", key, "=", layer[key])
robust_call("save_scene", {}, t=90)

# deterministic SceneView QA (set_scene_view -> SceneView capture)
for tgt, sz, pit, yw, nm in [
    ("WorldForestGLB", 70, 10, 35, "fv_final_forest"),
    ("WorldForestGLB", 160, 16, 38, "fv_final_forest_mid"),
    ("WorldTerrain", 480, 26, 40, "fv_final_wide"),
]:
    sv = robust_call("set_scene_view",
                      {"target": tgt, "size": sz, "pitch": pit, "yaw": yw},
                      t=30, retries=2)
    print(f"sv {tgt}:", json.dumps(sv)[:130])
    time.sleep(1.3)
    print("shot:", json.dumps(studio_capture_screenshot(name=nm))[:130])

print("FULL REALIZE+QA DONE ok=%s" % ok)
