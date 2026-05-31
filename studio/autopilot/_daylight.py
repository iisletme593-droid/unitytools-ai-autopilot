import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# tek gunes, gunduz acisi, parlak; HDRP'de DUSUK EV = PARLAK
L = rc("list_lights", {}, 15) or {}
arr = L.get("lights") or []
suns=[x for x in arr if "sun" in str(x.get("name","")).lower() or str(x.get("type","")).lower().startswith("dir")]
for s in suns[1:]: rc("delete_object", {"name": s.get("name")}, 10)
nm = suns[0].get("name") if suns else "Sun1"
if not suns:
    rc("create_light", {"light_type":"Directional","name":nm,"intensity":100000,"color":{"r":1,"g":0.97,"b":0.9}}, 18)
rc("set_light_properties", {"name":nm,"intensity":95000,"color":{"r":1.0,"g":0.97,"b":0.9},"shadows_enabled":True}, 15)
rc("set_rotation", {"name":nm,"x":45,"y":-30,"z":0}, 12)
rc("setup_hdrp_volume", {"fog":True,"fog_distance":600.0,"exposure_mode":"Fixed","fixed_exposure":11.4}, 20)
out.append("gunduz isik ayarlandi")
out.append("saved="+str(save()))
# net kareler
kp = pos_of("GothicCastle") or (-482,95,-311)
shot("day_castle", kp[0]+55, kp[1]+30, kp[2]+55, 110, 8, 220)
wp = pos_of("WoodHouse") or (-300,61,-120)
shot("day_house", wp[0]+16, wp[1]+7, wp[2]+16, 26, 5, 210)
cf = pos_of("Campfire") or (-526,142,-98)
shot("day_ground", cf[0]+7, cf[1]+5, cf[2]+7, 18, 30, 40)
out.append("shots: day_castle/house/ground")
Path("studio/autopilot/_daylight.txt").write_text("\n".join(out), encoding="utf-8")
