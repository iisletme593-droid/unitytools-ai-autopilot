"""Hybrid: C# optimized-forest call = clean + optimized terrain/light/
fog base (anti-'kasiyor'); then overlay REAL PolyHaven GLB trees/rocks
+ Warden hero with INSTANTIATE-ONLY (no post-transform -> no name race).
"""
import json, math, random
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

c, b, unity = _bootstrap(); unity.connect(timeout=5.0)
init_studio_unity(unity); ut._UNITY = unity
p = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in p.all_dirs()]
init_studio_tools(StudioState(p))

from unitytools.tools.unity_tools import (
    unity_open_scene, unity_list_scenes, unity_instantiate_prefab,
    unity_save_scene,
)
from unitytools.studio.tools import studio_capture_screenshot

unity_open_scene("Assets/Scenes/ForgottenValley_VS.unity")
act = [s for s in unity_list_scenes().get("scenes", []) if s.get("active")]
print("active:", act[0]["name"] if act else "?")

# 1) RAW C# call: clear everything + optimized terrain + morning light
#    + fog base. tree_count=1 (we bring real trees ourselves).
base = unity.call("create_optimized_forest_scene", {
    "clear_scene": True, "tree_count": 1, "rock_count": 0,
    "terrain_size": 110, "seed": 42,
})
print("base:", json.dumps(base)[:160] if not isinstance(base, str) else base[:160])

T = "Assets/Models/PolyHaven/Nature/Trees/"
R = "Assets/Models/PolyHaven/Nature/Rocks/"
PINE, FIR, DEAD = (T + "Nature_Trees_04_PineTree.glb",
                   T + "Nature_Trees_05_FirTree.glb",
                   T + "Nature_Trees_01_DeadTreeTrunk.glb")
BOULDER, ROCK7 = R + "Nature_Rocks_01_Boulder1.glb", R + "Nature_Rocks_02_Rock7.glb"
HERO = "Assets/Art/Characters/Imported/Hero/SK_Hero.fbx"

random.seed(42)
placed = 0
# 2) Real trees — INSTANTIATE ONLY, native scale, natural clustered ring.
for i in range(16):
    a = (i / 16) * math.tau + random.uniform(-0.15, 0.15)
    rad = 9 + (i % 4) * 5.5 + random.uniform(-1, 3)
    x, z = math.cos(a) * rad, math.sin(a) * rad
    src = PINE if i % 3 else FIR
    r = unity_instantiate_prefab(src, round(x, 2), 0.0, round(z, 2))
    if isinstance(r, dict) and r.get("ok"):
        placed += 1
print(f"real trees placed: {placed}/16")

for i, (x, z) in enumerate([(-6, 5), (7, 9), (-9, -7)]):
    unity_instantiate_prefab(DEAD, x, 0.0, z)

rk = 0
for x, z, src in [(-4, 3, BOULDER), (5, -2, ROCK7), (-8, -6, BOULDER),
                  (4, 8, ROCK7), (9, 4, BOULDER)]:
    r = unity_instantiate_prefab(src, x, 0.0, z)
    if isinstance(r, dict) and r.get("ok"):
        rk += 1
print(f"real rocks placed: {rk}/5")

hero = unity_instantiate_prefab(HERO, 0.0, 0.0, -3.0)
print("hero:", json.dumps(hero)[:120] if isinstance(hero, dict) else hero)

unity_save_scene()
print(json.dumps(studio_capture_screenshot(name="fv_hybrid_real"), indent=1)[:230])
print("HYBRID DONE")
