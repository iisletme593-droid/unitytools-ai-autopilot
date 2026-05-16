"""Stage 3 in-scene: make place_asset_on_terrain live (force-recompile
via the running bridge), wait for the main thread, then run the
DOCS-driven AI asset orchestrator (Blender -> Unity -> terrain).

Hardened: real main-thread probe + fresh reconnect each retry (unity.py
now nulls the socket on WinError 10053 / OSError so reconnect works).
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools, init_studio_blender)
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
try:
    init_studio_blender(b)
except Exception as e:
    print("blender init warn:", e)
import unitytools.studio.tools as st


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
            fresh_connect(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} failed x{retries}"}


def wait_main(tries=70, gap=7, tag="main"):
    from unitytools.bridges.unity import focus_unity_window
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
                print(f"[{tag}] ok ({dt:.2f}s) x{ok}")
                if ok >= 2: return True
            else:
                ok = 0; print(f"[{tag}] slow ({dt:.2f}s) #{i}")
        except Exception as e:
            ok = 0; print(f"[{tag}] busy #{i}: {str(e)[:50]}")
        time.sleep(gap)
    return False


print("== wait main thread (pre-recompile) ==")
if not wait_main(tag="pre"):
    print("STALLED pre-recompile; abort clean"); raise SystemExit(0)

# place_asset_on_terrain was added after the last compile -> recompile.
print("force-recompile:", json.dumps(robust_call("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs",
}, t=60, retries=2))[:140])
time.sleep(10)

print("== wait main thread (post-recompile) ==")
if not wait_main(tries=80, gap=7, tag="post"):
    print("STALLED post-recompile; abort clean"); raise SystemExit(0)

# confirm place_asset_on_terrain is live
probe = robust_call("place_asset_on_terrain", {"asset_path": "__none__"},
                    t=20, retries=2)
print("probe place_asset_on_terrain:", json.dumps(probe)[:160])

# DOCS-driven AI asset manufacture + placement (in-process tool)
print("== studio_generate_world_assets ==")
res = st.studio_generate_world_assets(dry_run=False)
print("RESULT:", json.dumps(res)[:900])

# QA: wide + a generated-prop close-up
from unitytools.studio.tools import studio_capture_screenshot
robust_call("set_scene_view", {"target": "WorldGeneratedProps",
                               "size": 90, "pitch": 16, "yaw": 40}, t=30)
time.sleep(1.2)
print("shot props:", json.dumps(studio_capture_screenshot(name="fv_ai_props"))[:140])
robust_call("set_scene_view", {"target": "WorldTerrain", "size": 520,
                               "pitch": 24, "yaw": 40}, t=30)
time.sleep(1.2)
print("shot wide:", json.dumps(studio_capture_screenshot(name="fv_ai_props_wide"))[:140])
print("WORLD ASSETS DONE placed=%s/%s" % (
    res.get("placed") if isinstance(res, dict) else "?",
    res.get("total") if isinstance(res, dict) else "?"))
