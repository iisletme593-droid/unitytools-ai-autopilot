"""BONUS: MASTER SAHNE KURMA — tek komutla tum kompozisyonu sifirdan kurar +
HER ADIMDA kaydeder. Domain-reload sahneyi ucurursa bunu calistir, geri gelir.

Kurar: orman (LP_Fir_GLB koyu) -> zemin PBR -> ev (woodhouse+doku) -> kale
(CastleV2+tas) -> kamp atesi isigi -> gunduz isik/exposure -> kahraman kampta.
Her buyuk adimdan sonra save_scene (timeout'a karsi parca parca).

Kullanim: python rebuild_scene.py [agac_sayisi=900]
"""
import sys, json, time, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *

PROJ = "C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject"
N_TREE = int(sys.argv[1]) if len(sys.argv) > 1 else 900
log = []
def step(msg): log.append(msg); Path("studio/autopilot/_rebuild.txt").write_text("\n".join(log), encoding="utf-8")

connect()
if not guard_scene():
    step("GUARD_FAIL"); raise SystemExit

# kamp merkezi (kalici objelerden referans)
cf = pos_of("Campfire") or pos_of("CampSite") or (-526, 142, -98)
cx, cy, cz = cf
step(f"merkez kamp=({cx:.0f},{cy:.0f},{cz:.0f})")

# 1) ORMAN (instance -> binary sahnede yasar; clear_primitive ile temiz baslar)
res = rc("scatter_terrain_glb_trees", {
    "models":["Assets/Art/HQ/LP_Fir_GLB.glb"],
    "dead_models":["Assets/Art/HQ/SolidDead.glb"],
    "foliage_material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_CardNeedle.mat",
    "trunk_material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_WetAgedWood.mat",
    "tree_count":N_TREE,"forest_min":0.05,"forest_max":0.62,"max_slope_deg":34.0,
    "scale_min":6.0,"scale_max":11.0,"dead_ratio":0.06,"seed":int(cx)%997,
    "clear_primitive_forest":True,"y_offset":-0.3}, 500)
time.sleep(1); fresh()
step("orman="+str(child_count("WorldForestGLB"))); step("save1="+str(rc("save_scene",{},60))[:20])

# 2) ZEMIN PBR (4 katman)
G="Assets/FantasyRPG/Textures/Ground"
def lyr(num,name,t): return {"name":name,
    "diffuse":f"{G}/Ground{num}/Ground{num}_2K-JPG_Color.jpg",
    "normal":f"{G}/Ground{num}/Ground{num}_2K-JPG_NormalGL.jpg","tile":t}
rc("apply_terrain_pbr_layers", {"layers":[lyr("054","Cayir",14),lyr("104","Orman",16),
    lyr("103","Toprak",18),lyr("037","Cakil",12)], "cutoffs":[0.30,0.58,0.82]}, 180)
fresh(); step("zemin PBR ok"); step("save2="+str(rc("save_scene",{},60))[:20])

# 3) EV (gercek woodhouse + doku)
for _ in range(2): rc("delete_object", {"name":"WoodHouse"}, 10)
ev=surf(cx+15, cz+8, cy)
r=rc("place_asset_on_terrain", {"asset_path":"Assets/70-woodhouse/WoodHouse/WoodHouse.fbx",
    "x":cx+15,"z":cz+8,"scale":0.75,"name":"WoodHouse","min_surface_y":0.0,
    "max_slope_deg":89.0,"search_radius":0.0,"y_offset":0.0}, 90)
if isinstance(r,dict) and r.get("ok"):
    rc("set_rotation", {"name":"WoodHouse","x":0,"y":150,"z":0}, 12)
    rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_WoodHouse.mat","name_contains":"WoodHouse","recurse":True}, 60)
step("ev="+("ok" if isinstance(r,dict) and r.get("ok") else "FAIL"))

# 4) KALE (CastleV2 + tas)
for _ in range(2): rc("delete_object", {"name":"GothicCastle"}, 10)
kx,kz=cx+10, cz-70; ky=surf(kx,kz,cy)
r=rc("place_asset_on_terrain", {"asset_path":"Assets/Art/HQ/CastleV2.fbx",
    "x":kx,"z":kz,"scale":2.2,"name":"GothicCastle","min_surface_y":0.0,
    "max_slope_deg":89.0,"search_radius":0.0,"y_offset":-1.5}, 120)
if isinstance(r,dict) and r.get("ok"):
    rc("set_rotation", {"name":"GothicCastle","x":0,"y":0,"z":0}, 12)
    rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_CastleStone.mat","name_contains":"GothicCastle","recurse":True}, 60)
step("kale="+("ok" if isinstance(r,dict) and r.get("ok") else "FAIL"))
step("save3="+str(rc("save_scene",{},60))[:20])

# 5) ISIK + EXPOSURE (gunduz)
L=rc("list_lights",{},15) or {}; arr=L.get("lights") or []
suns=[x for x in arr if "sun" in str(x.get("name","")).lower()]
nm=suns[0].get("name") if suns else "Sun1"
if not suns: rc("create_light",{"light_type":"Directional","name":nm,"intensity":95000,"color":{"r":1,"g":0.97,"b":0.9}},18)
rc("set_light_properties",{"name":nm,"intensity":95000,"color":{"r":1,"g":0.97,"b":0.9},"shadows_enabled":True},15)
rc("set_rotation",{"name":nm,"x":48,"y":-32,"z":0},12)
rc("setup_hdrp_volume",{"fog":True,"fog_distance":700.0,"exposure_mode":"Fixed","fixed_exposure":13.8},20)
# kamp atesi sicak isik
if not pos_of("CampfireLight"):
    rc("create_light",{"light_type":"Point","name":"CampfireLight","intensity":180,"range":18,"color":{"r":1,"g":0.55,"b":0.22},"position":{"x":cx,"y":cy+1.5,"z":cz}},18)
step("isik ok")

# 6) KAHRAMAN kampa
sy=surf(cx-4, cz-4, cy); rc("set_position",{"name":"SK_Hero","x":cx-4,"y":sy,"z":cz-4},12)
step("hero kampa")

step("FINAL_save="+str(rc("save_scene",{},60))[:20])
step("REBUILD_DONE forest="+str(child_count("WorldForestGLB")))
print("REBUILD_DONE")
