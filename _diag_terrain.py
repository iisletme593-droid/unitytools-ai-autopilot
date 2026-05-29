"""Diagnose why the terrain renders pale (no PBR layers showing).
Inspect: active render pipeline, terrain.materialTemplate shader,
HDRP/TerrainLit availability, terrainData layer count + textures.
"""
import json, time
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))

focus_unity_window(); time.sleep(1)
U.connect(timeout=8)


def call(cmd, p, t=40):
    try: return U.call(cmd, p, timeout=t)
    except Exception as e: return {"ok": False, "error": str(e)[:120]}


# get_object_details on WorldTerrain (components), and run a small
# eval-style probe via existing commands.
print("terrain details:", json.dumps(call("get_object_details", {"name": "WorldTerrain"}))[:400])
print("list_root (terrain pos):", json.dumps(call("list_root_objects", {}))[:300])
# run_visual_qa returns material health stats (broken/unsupported counts)
qa = call("run_visual_qa", {"capture_screenshot": False}, t=60)
print("visual_qa:", json.dumps(qa)[:600])
