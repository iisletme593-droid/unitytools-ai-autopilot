"""KAMP KAYALARI — gercek PolyHaven boulder mesh'leri + Rock058 grey-slate
malzeme, kamp cevresine DOGRU terrain yuksekliginde otur. Kullanici: 'gercek
kaya renkleri + tam haritadaki yere oturt'. Play KAPALI. CampRocks grubu (geri
alinabilir). Reliable seat: surf() + place_pinned search_radius=0.
"""
import sys, time, math, random, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

PH = "Assets/FantasyRPG/Models/PolyHaven/Nature/Rocks"
ROCKS = [
    f"{PH}/Nature_Rocks_01_Boulder1.glb",
    f"{PH}/Nature_Rocks_02_Rock7.glb",
    f"{PH}/Nature_Rocks_03_Rock9.glb",
    f"{PH}/Nature_Rocks_06_RockMossSet.glb",
]
MAT = "Assets/FantasyRPG/Generated/Materials/HDRP_M_WetRock.mat"

log = []
def L(m): log.append(m); Path("studio/autopilot/_camprocks.txt").write_text("\n".join(log), encoding="utf-8")

ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

# material reimport icin Assets/Refresh
ap.rc("execute_menu_item", {"path": "Assets/Refresh"}, 60); time.sleep(8); ap.fresh()
L("refresh ok")

cf = (-526.0, -98.0)  # kamp XZ
rng = random.Random(42)

for _ in range(2): ap.rc("delete_object", {"name": "CampRocks"}, 10)
sy0 = ap.surf(cf[0], cf[1], 142)
ap.rc("create_empty", {"name": "CampRocks", "position": {"x": cf[0], "y": sy0, "z": cf[1]}}, 12)

# kamp halkasi disinda (8-22m), dogal kumeler halinde 14 kaya
placed = 0
specs = []
# birkac buyuk capa kayasi + cevreye kucukler
anchors = [(10, 6), (-12, 4), (6, -13), (-8, -11), (14, -4), (-3, 15)]
for ax, az in anchors:
    big = rng.choice(ROCKS)
    specs.append((big, ax, az, rng.uniform(2.0, 3.4)))         # buyuk
    for _ in range(rng.randint(1, 2)):                          # cevresine kucuk
        specs.append((rng.choice(ROCKS), ax+rng.uniform(-3,3), az+rng.uniform(-3,3), rng.uniform(0.7,1.4)))

for i, (asset, dx, dz, sc) in enumerate(specs):
    nm = f"CampRock_{i:02d}"
    r = ap.place_pinned(asset, cf[0]+dx, cf[1]+dz, sc, nm, parent="CampRocks",
                        glb=True, rot_y=rng.uniform(0, 360), y_offset=-0.25,
                        min_surface_y=5.0, max_slope_deg=55.0)
    if r:
        ap.rc("assign_material_asset", {"material_path": MAT, "name_contains": nm, "recurse": True}, 14)
        placed += 1
    if placed and placed % 6 == 0: ap.fresh()
L(f"kaya_yerlesti={placed}/{len(specs)}")
L("CampRocks_cc=" + str(ap.child_count("CampRocks")))
L("forest=" + str(ap.child_count("WorldForestGLB")))
L("SAVE=" + str(ap.save()))
L("CAMPROCKS_DONE")
print("CAMPROCKS_DONE placed=%d" % placed)
