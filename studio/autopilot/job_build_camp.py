"""KAMP ALANI INSASI v1 — gercek RPG us merkezi. Oncelik #1.
Mevcut bos CampDressing/CampWarmth/CraftStation'i gercek proplarla doldur +
kamp atesi cevresinde KARES alan ac (agaclar cok yakin).

Gercek palet (diskte DOGRULANMIS):
  test_campfire.glb (1.5m fire pit) · SolidDead.glb (kütük/odun) · Rock_mossy.fbx
  + cliff_outcrop.fbx (ates halkasi taslari) · Environment_Lighting_01_Lantern.glb
  · Environment_Furniture_02_GothicCabinet.glb (depo) · Fern/GrassClump (yesillik)

Yontem: ap.place_pinned (search_radius=0, surf ile yukseklik, sabit koord).
Play KAPALI. Her sey 'CampHub' grubunda (geri alinabilir). Sonda save.
"""
import sys, time, math, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

U = "Assets"
CAMPFIRE = f"{U}/Art/Characters/Misc/test_campfire.glb"
DEADWOOD = f"{U}/Art/HQ/SolidDead.glb"
ROCK     = f"{U}/Art/HQ/Rock_mossy.fbx"        # FBX (Z-up)
LANTERN  = f"{U}/FantasyRPG/Models/PolyHaven/Environment/Lighting/Environment_Lighting_01_Lantern.glb"
CABINET  = f"{U}/FantasyRPG/Models/PolyHaven/Environment/Furniture/Environment_Furniture_02_GothicCabinet.glb"
FERN     = f"{U}/Art/HQ/Fern.glb"

log = []
def L(m): log.append(m); Path("studio/autopilot/_buildcamp.txt").write_text("\n".join(log), encoding="utf-8")

ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

# kamp merkezi: HearthEmber kalici referans (-526,142.6,-98)
cx, cy, cz = -526.0, 142.6, -98.0
sy = ap.surf(cx, cz, cy)  # gercek zemin
L(f"merkez=({cx},{cz}) zemin={sy:.1f}")

# ---- 1) KARES ALAN: kamp atesine cok yakin CampForest agaclarini disari it ----
# CampForest 57 cocuk; 9m icindekileri sil (kares alan). Cevre orman kalir.
cleared = 0
d = ap.rc("get_object_details", {"name": "CampForest"}, 20) or {}
kids = d.get("children") or []
for k in kids:
    nm = k.get("name") if isinstance(k, dict) else str(k)
    p = k.get("position") if isinstance(k, dict) else None
    if not p:
        dd = ap.rc("get_object_details", {"name": nm}, 8) or {}
        p = dd.get("position")
    if p:
        dist = math.hypot(p.get("x", 0) - cx, p.get("z", 0) - cz)
        if dist < 10.0:
            ap.rc("delete_object", {"name": nm}, 8)
            cleared += 1
L(f"kares_alan: {cleared} yakin agac silindi (10m)")
ap.fresh()

# ---- grup ----
for _ in range(2): ap.rc("delete_object", {"name": "CampHub"}, 8)
ap.rc("create_empty", {"name": "CampHub", "position": {"x": cx, "y": sy, "z": cz}}, 12)

def place(asset, dx, dz, scale, name, glb=True, ry=0.0, yoff=0.0):
    r = ap.place_pinned(asset, cx + dx, cz + dz, scale, name, parent="CampHub",
                        glb=glb, rot_y=ry, y_offset=yoff, min_surface_y=5.0, max_slope_deg=50.0)
    return bool(r)

placed = 0

# ---- 2) KAMP ATESI (merkez) ----
if place(CAMPFIRE, 0, 0, 1.2, "CampfireModel", glb=True, yoff=0.0): placed += 1
L(f"campfire={placed>0}")

# ---- 3) ATES HALKASI: 7 tas cevrede (r=2.2m) ----
rng_ok = 0
for i in range(7):
    a = i * (math.tau / 7)
    dx, dz = math.cos(a) * 2.2, math.sin(a) * 2.2
    if place(ROCK, dx, dz, 0.5, f"FireStone_{i}", glb=False, ry=i*53, yoff=-0.15):
        ap.color(f"FireStone_{i}", 0.30, 0.30, 0.31, smooth=0.1)
        rng_ok += 1
L(f"ates_halkasi={rng_ok}/7")

# ---- 4) KUTUK OTURAKLAR: 4 yatık kütük (r=4m), ates etrafinda ----
seat_ok = 0
for i in range(4):
    a = i * (math.tau / 4) + 0.4
    dx, dz = math.cos(a) * 4.0, math.sin(a) * 4.0
    nm = f"LogSeat_{i}"
    # SolidDead'i yatay yatık kütük yap: rot_x ile devir (ap set_rotation glb=>x0; sonra elle yatir)
    if place(DEADWOOD, dx, dz, 0.7, nm, glb=True, ry=math.degrees(a)+90, yoff=0.0):
        # yatay yatir: govdeyi 90 deg X dondur, alcalt
        ap.rc("set_rotation", {"name": nm, "x": 90, "y": math.degrees(a)+90, "z": 0}, 10)
        ap.color(nm, 0.28, 0.19, 0.11, smooth=0.12)
        seat_ok += 1
L(f"kutuk_oturak={seat_ok}/4")

# ---- 5) ODUN YIGINI (atese yakin) ----
wood_ok = 0
for i in range(3):
    nm = f"Firewood_{i}"
    if place(DEADWOOD, -3.0 + i*0.4, 2.6, 0.4, nm, glb=True, ry=80+i*15, yoff=0.0):
        ap.rc("set_rotation", {"name": nm, "x": 88, "y": 80+i*15, "z": 0}, 10)
        ap.color(nm, 0.30, 0.20, 0.11, smooth=0.1)
        wood_ok += 1
L(f"odun_yigini={wood_ok}/3")

# ---- 6) DEPO: GothicCabinet + (chest yoksa cabinet x2) ----
store_ok = 0
if place(CABINET, 6.5, -3.0, 1.6, "CampStorage", glb=True, ry=210): store_ok += 1
if place(CABINET, 8.0, -1.5, 1.3, "CampStorage2", glb=True, ry=160): store_ok += 1
L(f"depo={store_ok}/2")

# ---- 7) LANTERNLER (sicak isik direkleri) ----
lant_ok = 0
for i, (dx, dz) in enumerate([(-5, -4), (5, 4), (-2, 6)]):
    nm = f"CampLantern_{i}"
    if place(LANTERN, dx, dz, 2.0, nm, glb=True, ry=i*40):
        lant_ok += 1
        # her lanterne kucuk sicak point isik
        ls = ap.surf(cx+dx, cz+dz, sy)
        ap.rc("create_light", {"light_type": "Point", "name": f"LanternLight_{i}",
              "intensity": 140, "range": 8, "color": {"r": 1.0, "g": 0.66, "b": 0.32},
              "position": {"x": cx+dx, "y": ls+1.8, "z": cz+dz}}, 14)
        ap.rc("set_parent", {"child": f"LanternLight_{i}", "parent": "CampHub"}, 8)
L(f"lantern={lant_ok}/3")

# ---- 8) FERN/yesillik kume (kamp kenari yumusatma) ----
fern_ok = 0
import random
rng = random.Random(7)
for i in range(8):
    a = rng.uniform(0, math.tau); rad = rng.uniform(6, 9)
    if place(FERN, math.cos(a)*rad, math.sin(a)*rad, rng.uniform(1.0,1.6), f"CampFern_{i}",
             glb=True, ry=rng.uniform(0,360), yoff=-0.05):
        ap.color(f"CampFern_{i}", 0.17, 0.31, 0.12, smooth=0.16)
        fern_ok += 1
L(f"fern={fern_ok}/8")

# ---- kamp atesi isigi + kor (varsa koru, yoksa kur) ----
if not (ap.rc("get_object_details", {"name": "CampfireLight"}, 8) or {}).get("name"):
    ap.rc("create_light", {"light_type": "Point", "name": "CampfireLight",
          "intensity": 900, "range": 20, "color": {"r": 1.0, "g": 0.52, "b": 0.2},
          "position": {"x": cx, "y": sy+1.4, "z": cz}}, 14)
    ap.rc("set_parent", {"child": "CampfireLight", "parent": "CampHub"}, 8)

L("SAVE=" + str(ap.save()))
L("CampHub_cc=" + str(ap.child_count("CampHub")))
L("forest=" + str(ap.child_count("WorldForestGLB")))
L("BUILD_CAMP_DONE")
print("BUILD_CAMP_DONE")
