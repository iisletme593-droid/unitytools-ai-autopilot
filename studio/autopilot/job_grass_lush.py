"""Cekirdek kampi GUR cim yap: 0-22m'ye buyuk olcekli yogun tutam.
Gorsel teyitle (grasscheck 144332): on plan cipak gri zemin -> 270 tutam cok
seyrek. Bu job cekirdege buyuk+yogun ekler. Play KAPALI."""
import sys, time, math, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
ADD = int(sys.argv[1]) if len(sys.argv) > 1 else 400
GRASS = "Assets/Art/HQ/GrassBladeClump.glb"
MAT = "Assets/FantasyRPG/Generated/Materials/HDRP_M_GrassBlade.mat"
out = []
connect()
es = rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    rc("play_mode", {"play": False}, 40); time.sleep(3); fresh()
guard_scene()
start = child_count("VegGrass") or 0
out.append("start=" + str(start))
cf = pos_of("Campfire") or (-526, 142, -98)
rng = random.Random(123)
n = 0; tries = 0
while n < ADD and tries < ADD * 4:
    tries += 1
    a = rng.uniform(0, math.tau)
    rad = rng.uniform(2, 22) ** 0.85  # cekirdege yogunlasma
    rad = 2 + (22-2) * (rng.random() ** 0.6)  # ic kisim daha yogun
    x = cf[0] + math.cos(a) * rad; z = cf[2] + math.sin(a) * rad
    nm = f"VegGrass_{start+n:04d}"
    r = place_pinned(GRASS, x, z, rng.uniform(2.5, 4.5), nm, parent="VegGrass",
                     glb=True, rot_y=rng.uniform(0, 360), y_offset=-0.05,
                     min_surface_y=5.0, max_slope_deg=45.0)
    if r:
        n += 1
        if n % 50 == 0: fresh()
out.append(f"eklendi={n} ({tries})")
rc("assign_material_asset", {"material_path": MAT, "name_contains": "VegGrass", "recurse": True}, 150)
out.append("VegGrass_toplam=" + str(child_count("VegGrass")))
out.append("forest=" + str(child_count("WorldForestGLB")))
out.append("SAVE=" + str(save())[:10])
Path("studio/autopilot/_lush.txt").write_text("\n".join(out), encoding="utf-8")
print("LUSH_DONE")
