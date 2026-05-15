"""Rebuild ForgottenValley_VS with REAL PolyHaven assets + the Warden
hero, replacing the primitive greybox. Uses returned instance names
so per-object transform sticks even with auto-suffixed duplicates.
"""
import json, math, random
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

c, b, unity = _bootstrap(); unity.connect(timeout=4.0)
init_studio_unity(unity); ut._UNITY = unity
p = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in p.all_dirs()]
init_studio_tools(StudioState(p))

from unitytools.tools.unity_tools import (
    unity_open_scene, unity_list_scenes, unity_list_scene_objects,
    unity_delete_object, unity_instantiate_prefab, unity_set_position,
    unity_set_scale, unity_set_rotation, unity_save_scene,
)
from unitytools.studio.tools import studio_capture_screenshot

random.seed(20)
TREES = "Assets/Models/PolyHaven/Nature/Trees/"
ROCKS = "Assets/Models/PolyHaven/Nature/Rocks/"
PINE = TREES + "Nature_Trees_04_PineTree.glb"
FIR  = TREES + "Nature_Trees_05_FirTree.glb"
DEAD = TREES + "Nature_Trees_01_DeadTreeTrunk.glb"
BOULDER = ROCKS + "Nature_Rocks_01_Boulder1.glb"
ROCK7 = ROCKS + "Nature_Rocks_02_Rock7.glb"
ROCKFACE = ROCKS + "Nature_Rocks_04_RockFace1.glb"
HERO = "Assets/Art/Characters/Imported/Hero/SK_Hero.fbx"

# scene-revert guard
unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")
act = [s for s in unity_list_scenes().get("scenes", []) if s.get("active")]
print("active:", act[0]["name"] if act else "?")

# 1) Strip the primitive blockout (keep Ground, Sun_Golden, Hearth_*, Main Camera)
o = unity_list_scene_objects()
names = [(x if isinstance(x, str) else x.get("name")) for x in o.get("objects", [])]
killed = 0
for n in names:
    if not n:
        continue
    if (n.startswith(("Pine_", "PineNear_", "Rock_", "Pass_"))
            or n == "Nature_Trees_04_PineTree"):
        r = unity_delete_object(n)
        if isinstance(r, dict) and r.get("ok"):
            killed += 1
print(f"stripped {killed} primitive/test objects")

def place(path, x, y, z, sx, sy, sz, ry, label):
    r = unity_instantiate_prefab(path, round(x, 2), y, round(z, 2))
    if not (isinstance(r, dict) and r.get("ok")):
        print("ERR place", label, r); return None
    nm = r.get("name")
    unity_set_scale(nm, sx, sy, sz)
    unity_set_rotation(nm, 0, ry, 0)
    return nm

# 2) Pine/fir forest — clustered ring 8..34m, varied scale+yaw.
forest = 0
for i in range(22):
    a = (i / 22) * math.tau + random.uniform(-0.12, 0.12)
    rad = 8 + (i % 5) * 5.0 + random.uniform(-1.5, 2.5)
    x, z = math.cos(a) * rad, math.sin(a) * rad
    src = PINE if i % 3 else FIR
    sc = random.uniform(0.85, 1.5)
    if place(src, x, 0.0, z, sc, sc * random.uniform(0.9, 1.25), sc,
             random.uniform(0, 360), f"tree{i}"):
        forest += 1
print(f"forest: {forest} real trees")

# 3) Moody dead-tree accents near the sightline
for i, (x, z) in enumerate([(-5, 5), (6.5, 9), (-8, -6)]):
    place(DEAD, x, 0.0, z, random.uniform(1.0, 1.6),
          random.uniform(1.1, 1.7), random.uniform(1.0, 1.6),
          random.uniform(0, 360), f"dead{i}")

# 4) Real rocks scattered
for i, (x, z, src) in enumerate([
        (-4, 3, BOULDER), (5, -2, ROCK7), (-7, -7, BOULDER),
        (3.5, 8, ROCK7), (9, 4, BOULDER)]):
    s = random.uniform(0.8, 1.6)
    place(src, x, 0.0, z, s, s, s, random.uniform(0, 360), f"rock{i}")

# 5) Sealed pass: two big RockFace slabs at +Z (biome-2 teaser)
place(ROCKFACE, -3.0, 0.0, 30.0, 2.4, 3.0, 2.0, 20, "passL")
place(ROCKFACE, 3.2, 0.0, 30.0, 2.4, 3.0, 2.0, -160, "passR")

# 6) The Warden hero near the hearth as the player stand-in
h = place(HERO, 0.0, 0.0, -2.5, 1.0, 1.0, 1.0, 0, "hero")
print("hero:", h)

unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_real_assets"), indent=1)[:240])
print("REAL VALLEY DONE")
