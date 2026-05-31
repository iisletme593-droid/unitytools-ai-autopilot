import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# gunduz isigi garantile: tek gunes, dusuk EV = parlak
L = rc("list_lights", {}, 15) or {}
arr=L.get("lights") or []
suns=[x for x in arr if "sun" in str(x.get("name","")).lower() or str(x.get("type","")).lower().startswith("dir")]
for s in suns[1:]: rc("delete_object", {"name":s.get("name")}, 10)
nm=suns[0].get("name") if suns else "Sun1"
if not suns: rc("create_light",{"light_type":"Directional","name":nm,"intensity":100000,"color":{"r":1,"g":0.97,"b":0.9}},18)
rc("set_light_properties",{"name":nm,"intensity":95000,"color":{"r":1.0,"g":0.97,"b":0.9},"shadows_enabled":True},15)
rc("set_rotation",{"name":nm,"x":48,"y":-35,"z":0},12)
rc("setup_hdrp_volume",{"fog":True,"fog_distance":700.0,"exposure_mode":"Fixed","fixed_exposure":11.2},20)
out.append("gunduz ok")
kp = pos_of("GothicCastle") or (-482,95,-311)
out.append("kale="+str(kp))
# uzaktan 3 aci
for tag,(dx,dy,dz,sz,pit,yaw) in {
    "kc_a":(70,40,70,140,10,220),
    "kc_b":(90,55,0,150,14,270),
    "kc_c":(0,45,90,130,10,180)}.items():
    rc("set_scene_view",{"pivot_x":kp[0],"pivot_y":kp[1]+18,"pivot_z":kp[2],"size":sz,"pitch":pit,"yaw":yaw},30)
    time.sleep(1.2)
    from ap import _studio_shot
    _studio_shot(name=tag)
out.append("shots kc_a/b/c")
Path("studio/autopilot/_castleshot.txt").write_text("\n".join(out), encoding="utf-8")
