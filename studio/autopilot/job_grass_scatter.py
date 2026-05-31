"""Gercek cim bicagi tutamlarini (GrassBladeClump.glb) kamp+orman bandina scatter.
Malzeme TEK toplu cagri ile sonda atanir (timeout'a karsi). Orman'a DOKUNMAZ.
Play KAPALI.
"""
import sys, time, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *

N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
GRASS = "Assets/Art/HQ/GrassBladeClump.glb"
MAT = "Assets/FantasyRPG/Generated/Materials/HDRP_M_GrassBlade.mat"
out = []
connect()
es = rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    rc("play_mode", {"play": False}, 40); time.sleep(3); fresh()
guard_scene()
out.append("forest_before=" + str(child_count("WorldForestGLB")))

# eski prosedurel cim gruplarini temizle
for nm in ("WorldGrass", "GrassField"):
    for _ in range(2): rc("delete_object", {"name": nm}, 10)

cf = pos_of("Campfire") or (-526, 142, -98)
empty("VegGrass", cf[0], cf[1], cf[2])
rng = random.Random(50)
n = 0; tries = 0
while n < N and tries < N * 4:
    tries += 1
    a = rng.uniform(0, math.tau); rad = rng.uniform(5, 90)
    x = cf[0] + math.cos(a) * rad; z = cf[2] + math.sin(a) * rad
    nm = f"VegGrass_{n:03d}"
    r = place_pinned(GRASS, x, z, rng.uniform(1.2, 2.6), nm, parent="VegGrass",
                     glb=True, rot_y=rng.uniform(0, 360), y_offset=-0.04,
                     min_surface_y=5.0, max_slope_deg=40.0)
    if r:
        n += 1
        if n % 40 == 0: fresh()
out.append(f"yerlesti={n} ({tries} deneme)")
# TEK toplu malzeme atamasi
rc("assign_material_asset", {"material_path": MAT, "name_contains": "VegGrass", "recurse": True}, 90)
out.append("VegGrass_child=" + str(child_count("VegGrass")))
out.append("forest_after=" + str(child_count("WorldForestGLB")))
out.append("SAVE=" + str(save())[:18])
Path("studio/autopilot/_grassscatter.txt").write_text("\n".join(out), encoding="utf-8")
print("GRASS_SCATTER_DONE")
