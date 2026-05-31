import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_rh.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
# eski basit evi sil
for _ in range(3): rc("delete_object", {"name":"WoodHouse"}, 12)
# gercek model kamp yanina
cf = pos_of("Campfire") or pos_of("CampSite") or (-533,137,-105)
hx, hz = cf[0]+16, cf[2]+10
WH = "Assets/70-woodhouse/WoodHouse/WoodHouse.fbx"
r = rc("place_asset_on_terrain", {"asset_path":WH,"x":hx,"z":hz,"scale":3.0,
    "name":"WoodHouse","min_surface_y":0.0,"max_slope_deg":89.0,"search_radius":0.0,"y_offset":0.0}, 90)
out.append("place="+json.dumps(r)[:120])
# HDRP doku malzemesi ata (tum renderer'lara)
am = rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_WoodHouse.mat",
    "name_contains":"WoodHouse","recurse":True}, 60)
out.append("mat="+json.dumps(am)[:140])
out.append("hero_pos_unchanged="+str(pos_of("SK_Hero")))
out.append("saved="+str(save()))
# rotasyon denemesi icin once cek (rot 0 hali)
shot("house_try0", hx+14, cf[1]+6, hz+14, 24, 5, 210)
Path("studio/autopilot/_rh.txt").write_text("\n".join(out), encoding="utf-8")
