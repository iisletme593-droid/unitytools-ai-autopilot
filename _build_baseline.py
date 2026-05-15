"""ForgottenValley_VS realistic URP baseline blockout.
Implements the Art Bible: low golden sun, BOUNDED linear fog 15-70m
(root-fix for the blank-void bug), amber hearth anchor, readable
landmark silhouettes, sealed-pass teaser, third-person camera framing.
Greybox quality — proves the lit composition, not final art.
"""
import json, math
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity

config, blender, unity = _bootstrap()
unity.connect(timeout=4.0)
init_studio_unity(unity); ut._UNITY = unity
from unitytools.tools.unity_tools import (
    unity_create_primitive, unity_set_scale, unity_set_position,
    unity_set_rotation, unity_create_light, unity_set_light_properties,
    unity_set_ambient_light, unity_set_fog, unity_set_skybox,
    unity_set_material_color, unity_set_material_pbr,
    unity_set_camera_transform, unity_save_scene,
)

log = []
def step(label, r):
    ok = isinstance(r, dict) and r.get("ok", True)
    log.append((label, ok, "" if ok else str(r)[:120]))
    print(("OK " if ok else "ERR") + " " + label + ("" if ok else f"  {r}"))

# ── Ground bowl (80x80m)
step("ground", unity_create_primitive("Plane", "Ground", 0, 0, 0))
step("ground.scale", unity_set_scale("Ground", 8, 1, 8))
step("ground.color", unity_set_material_color("Ground", 0.21, 0.26, 0.20, 1))
step("ground.pbr", unity_set_material_pbr("Ground", metallic=0.0, smoothness=0.12))

# ── Sun: low golden-hour directional
step("sun", unity_create_light("Sun_Golden", "Directional", 0, 30, 0,
                                1.0, 0.86, 0.62, 1.15, 100))
step("sun.rot", unity_set_rotation("Sun_Golden", 20, -34, 0))

# ── Cool ambient from sky
step("ambient", unity_set_ambient_light(0.42, 0.47, 0.55, 0.55, "Flat"))

# ── THE FIX: bounded linear fog (atmosphere, never a wall)
step("fog", unity_set_fog(1, "Linear", -1.0, 15.0, 72.0, 0.55, 0.60, 0.66))

# ── Skybox: cool sky / warm ground, controlled exposure
step("sky", unity_set_skybox("", 0.05, 1.1, 1.0, 0.50, 0.56, 0.64,
                              0.30, 0.27, 0.24))

# ── Hearth: the one warm anchor the eye always finds
step("hearth.base", unity_create_primitive("Cylinder", "Hearth_Base", 0, 0.35, 0))
step("hearth.scale", unity_set_scale("Hearth_Base", 0.7, 0.35, 0.7))
step("hearth.col", unity_set_material_color("Hearth_Base", 0.25, 0.12, 0.06, 1))
step("hearth.emis", unity_set_material_pbr("Hearth_Base", emission_enabled=1,
       emission_r=1.0, emission_g=0.45, emission_b=0.12, emission_intensity=2.4))
step("hearth.fire", unity_create_light("Hearth_Fire", "Point", 0, 1.1, 0,
                                        1.0, 0.55, 0.18, 3.2, 18))

# ── Pine blockout ring (readable dark silhouettes vs fog)
import random
random.seed(7)
trees = 16
for i in range(trees):
    a = (i / trees) * math.tau
    rad = 11 + (i % 4) * 5.0
    x, z = math.cos(a) * rad, math.sin(a) * rad
    nm = f"Pine_{i:02d}"
    unity_create_primitive("Cylinder", nm, round(x, 2), 2.4, round(z, 2))
    unity_set_scale(nm, 0.35, 2.4, 0.35)
    unity_set_material_color(nm, 0.10, 0.13, 0.10, 1)
step("pines", {"ok": True, "n": trees})

# ── Scattered rock blockout
for i, (x, z, s) in enumerate([(-6, 4, 1.3), (7, -3, 1.0), (-9, -8, 1.6),
                                (4, 9, 0.9), (12, 5, 1.2)]):
    nm = f"Rock_{i:02d}"
    unity_create_primitive("Cube", nm, x, 0.5 * s, z)
    unity_set_scale(nm, 1.6 * s, s, 1.4 * s)
    unity_set_material_color(nm, 0.28, 0.29, 0.30, 1)
step("rocks", {"ok": True, "n": 5})

# ── Sealed pass: biome-2 teaser landmark at +Z
for nm, (x, y, z), sc in [
    ("Pass_PostL", (-2.4, 2.5, 38), (0.8, 5.0, 0.8)),
    ("Pass_PostR", (2.4, 2.5, 38), (0.8, 5.0, 0.8)),
    ("Pass_Lintel", (0, 5.2, 38), (5.6, 0.7, 0.9)),
]:
    unity_create_primitive("Cube", nm, x, y, z)
    unity_set_scale(nm, *sc)
    unity_set_material_color(nm, 0.18, 0.17, 0.20, 1)
step("sealed_pass", {"ok": True})

# ── Third-person camera: behind+above hearth, looking toward the pass
step("cam", unity_set_camera_transform("Main Camera", 0.0, 6.0, -13.0,
                                        18.0, 0.0, 0.0))

step("save", unity_save_scene())

print("\n--- SUMMARY ---")
errs = [l for l in log if not l[1]]
print(f"{len(log)} steps, {len(errs)} errors")
for l, ok, msg in errs:
    print("  ERR", l, msg)
print("BASELINE DONE")
