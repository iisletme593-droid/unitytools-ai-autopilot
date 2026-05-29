"""Phase 111 final: recompile (ResolveSceneTerrain fix -> all terrain
handlers now target WorldTerrain, not the small leftover terrain), then
full studio_realize_world (sun + real PBR ground + water + real GLB
trees + Fixed exposure + HDRP volume) ALL on WorldTerrain, an explicit
fix_terrain_hdrp_material belt-and-suspenders, then deterministic QA.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
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
            print(f"  {cmd} fail#{k}: {str(e)[:50]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries}"}


def wait_main(tries=110, gap=7, tag="main"):
    ok = 0
    for i in range(tries):
        if i % 3 == 0:
            focus_unity_window()
        fresh()
        t0 = time.time()
        try:
            r = U.call("list_root_objects", {}, timeout=22)
            if isinstance(r, dict) and r.get("ok") and time.time() - t0 < 6.0:
                ok += 1; print(f"[{tag}] ok x{ok}")
                if ok >= 2: return True
            else: ok = 0
        except Exception as e:
            ok = 0; print(f"[{tag}] busy #{i}: {str(e)[:45]}")
        time.sleep(gap)
    return False


print("== wait main (pre) ==")
if not wait_main(tag="pre"): print("stalled pre"); raise SystemExit(0)
print("recompile:", json.dumps(rcall("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs"}, t=60, retries=2))[:120])
time.sleep(10)
print("== wait main (post) ==")
if not wait_main(tries=120, tag="post"): print("stalled post"); raise SystemExit(0)

# confirm which terrain the handlers now resolve
fix = rcall("fix_terrain_hdrp_material", {}, t=60, retries=2)
print("FIX TERRAIN:", json.dumps(fix)[:300])

print("== full realize (targets WorldTerrain now) ==")
rw = st.studio_realize_world(water_level=0.085, forest_count=240, relief_m=190.0)
print("REALIZE ok=%s" % (isinstance(rw, dict) and rw.get("ok")))
for layer in (rw.get("layers", []) if isinstance(rw, dict) else []):
    if isinstance(layer, dict):
        for k in ("biome_kind", "forest_kind"):
            if k in layer: print("  ", k, "=", layer[k])

# belt-and-suspenders: ensure WorldTerrain material is HDRP/TerrainLit
fix2 = rcall("fix_terrain_hdrp_material", {"terrain_name": "WorldTerrain"}, t=60, retries=2)
print("FIX2:", json.dumps(fix2)[:240])
rcall("save_scene", {}, t=90)

for tgt, sz, pit, yw, nm in [
    ("WorldForestGLB", 65, 8, 35, "fv_ok_forest"),
    ("WorldForestGLB", 170, 16, 38, "fv_ok_mid"),
    ("SK_Hero", 30, 6, 30, "fv_ok_hero"),
]:
    rcall("set_scene_view", {"target": tgt, "size": sz, "pitch": pit,
                             "yaw": yw}, t=30, retries=2)
    time.sleep(1.3)
    print(f"shot {nm}:", json.dumps(studio_capture_screenshot(name=nm))[:115])
print("REALIZE_FIXED DONE")
