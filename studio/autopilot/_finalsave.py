import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out={}
# gunduz isigi geri (kare karanliklti)
L=rc("list_lights",{},15) or {}; arr=L.get("lights") or []
suns=[x for x in arr if "sun" in str(x.get("name","")).lower()]
nm=suns[0].get("name") if suns else "Sun1"
rc("set_light_properties",{"name":nm,"intensity":95000,"color":{"r":1,"g":0.97,"b":0.9},"shadows_enabled":True},15)
rc("set_rotation",{"name":nm,"x":48,"y":-32,"z":0},12)
rc("setup_hdrp_volume",{"fog":True,"fog_distance":700.0,"exposure_mode":"Fixed","fixed_exposure":13.8},20)
# kahramani kampa geri
cf=pos_of("Campfire") or (-526,142,-98)
sy=surf(cf[0]-4, cf[2]-4, cf[1])
rc("set_position",{"name":"SK_Hero","x":cf[0]-4,"y":sy,"z":cf[2]-4},12)
out["forest"]=child_count("WorldForestGLB")
out["save"]=str(rc("save_scene",{},60))[:30]
time.sleep(1)
out["forest_final"]=child_count("WorldForestGLB")
Path("studio/autopilot/_fs.txt").write_text(json.dumps(out), encoding="utf-8")
