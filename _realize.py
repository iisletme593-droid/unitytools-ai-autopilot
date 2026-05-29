"""Run the Phase 96 intelligence layer: studio_realize_world.
No recompile — composes already-compiled bridge handlers.
"""
import json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

c, b, unity = _bootstrap(); unity.connect(timeout=6.0)
init_studio_unity(unity); ut._UNITY = unity
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
init_studio_tools(StudioState(P))

from unitytools.studio.tools import studio_realize_world, studio_capture_screenshot
r = studio_realize_world(water_level=0.10, forest_count=240, relief_m=1168.0)
print("REALIZE:", json.dumps(r, default=str)[:700])
shot = studio_capture_screenshot(name="fv_realized")
print("SHOT:", json.dumps(shot)[:170] if isinstance(shot, dict) else str(shot)[:170])
print("REALIZE DONE")
