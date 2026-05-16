"""Phase 106 Stage 1: replace the cube/cylinder placeholder pines with
REAL GLB tree models on the terrain surface.

Self-recompiling: the OLD running bridge has `import_asset` which does
AssetDatabase.Refresh() + ImportAsset(ForceUpdate). We force-reimport the
freshly-installed CommandHandlers.cs through it -> Unity recompiles the
domain -> the new `scatter_terrain_glb_trees` handler goes live with NO
manual Ctrl+R. Then idle-wait (poll ping, fast x3) and run the scatter.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import (init_studio_unity, StudioPaths, StudioState,
                               init_studio_tools)
from pathlib import Path

PROJ = "C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject"
SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap(); U.connect(timeout=8.0)
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))


def call(cmd, p, t=120):
    try:
        return U.call(cmd, p, timeout=t)
    except Exception as e:
        return {"ok": False, "error": str(e)[:150]}


def wait_idle(tag, tries=50, gap=6):
    idle = 0
    for attempt in range(tries):
        t0 = time.time()
        try:
            U.call("ping", {}, timeout=8)
            dt = time.time() - t0
            if dt < 1.5:
                idle += 1
                if idle >= 3:
                    print(f"[{tag}] Unity idle (ping {dt:.2f}s x{idle})")
                    return True
            else:
                idle = 0
                print(f"[{tag}] busy (ping {dt:.2f}s) #{attempt}")
        except Exception as e:
            idle = 0
            print(f"[{tag}] busy/timeout #{attempt}: {str(e)[:50]}")
            try:
                U.connect(timeout=5.0)
            except Exception:
                pass
        time.sleep(gap)
    print(f"[{tag}] still busy after {tries} tries")
    return False


# 0) make sure Unity is responsive before we poke it
wait_idle("pre")

# 1) force-reimport the new CommandHandlers.cs through the OLD bridge ->
#    AssetDatabase.Refresh + ForceUpdate import -> domain recompile.
print("force-recompile:", json.dumps(call("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs",
}, t=60))[:160])

# 2) recompile = domain reload; bridge drops + Unity busy. Wait it out.
time.sleep(8)
if not wait_idle("recompile", tries=60, gap=6):
    raise SystemExit("Unity did not settle after recompile")

# 3) new handler should be live now. Open the slice scene.
print("open:", json.dumps(call("open_scene",
      {"path": "Assets/Scenes/ForgottenValley_VS.unity"}))[:120])

# 4) replace the procedural WorldForest with REAL GLB trees.
res = call("scatter_terrain_glb_trees", {
    "tree_count": 260, "forest_min": 0.13, "forest_max": 0.55,
    "max_slope_deg": 34, "scale_min": 0.55, "scale_max": 1.6,
    "dead_ratio": 0.13, "seed": 11, "clear_primitive_forest": True,
}, t=180)
print("GLB TREES:", json.dumps(res)[:480])

if isinstance(res, dict) and res.get("ok"):
    call("save_scene", {})
    from unitytools.studio.tools import studio_capture_screenshot
    shot = studio_capture_screenshot(name="fv_real_trees")
    print("shot:", json.dumps(shot)[:160])
    print("REAL TREES DONE placed=%s fixed=%s kept=%s" % (
        res.get("placed"), res.get("renderers_fixed"),
        res.get("renderers_kept")))
else:
    print("SCATTER FAILED — handler may not be compiled yet:", res)
