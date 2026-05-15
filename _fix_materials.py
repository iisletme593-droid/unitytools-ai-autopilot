"""Fix the white GLB tree materials (non-URP shaders) + reframe camera.
All runtime RPCs — no reinstall.
"""
import json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.core.tool_registry import get_all_tools
from pathlib import Path

c, b, unity = _bootstrap(); unity.connect(timeout=5.0)
init_studio_unity(unity); ut._UNITY = unity
p = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in p.all_dirs()]
init_studio_tools(StudioState(p))

T = {t.name: t.fn for t in get_all_tools()}
from unitytools.tools.unity_tools import (
    unity_open_scene, unity_list_scenes, unity_set_camera_transform,
    unity_save_scene,
)
from unitytools.studio.tools import studio_capture_screenshot

unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")
act = [s for s in unity_list_scenes().get("scenes", []) if s.get("active")]
print("active:", act[0]["name"] if act else "?")

# 1) Diagnose what's broken
diag = T["unity_diagnose_material_issues"](max=40)
print("diagnose:", json.dumps(diag)[:300] if isinstance(diag, dict) else str(diag)[:300])

# 2) Repair incl. non-pipeline shaders (the white GLB tree fix),
#    textures preserved, no recolor.
rep = T["unity_repair_material_issues"](include_unsupported=True, tint=False, max=400)
print("repair:", json.dumps(rep)[:300] if isinstance(rep, dict) else str(rep)[:300])

# 3) Also run the auto-convert pass for anything still off-pipeline
conv = T["unity_auto_convert_materials_to_pipeline"](max=400)
print("convert:", json.dumps(conv)[:300] if isinstance(conv, dict) else str(conv)[:300])

# 4) Reframe: eye-level third-person, behind+above hero looking into
#    the valley so we see ground + forest depth + the hero, not canopy.
unity_set_camera_transform("Main Camera", 0.0, 3.0, -10.0, 6.0, 0.0, 0.0)

unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_real_fixed"), indent=1)[:230])
print("FIX DONE")
