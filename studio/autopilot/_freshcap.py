import sys, json, time, math, shutil, os; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# Play kapali oldugundan emin
es=rc("get_editor_state",{},15) or {}
if es.get("is_playing"): rc("play_mode",{"play":False},40); time.sleep(3); fresh()
# isik garanti
L=rc("list_lights",{},15) or {}; suns=[x for x in (L.get('lights') or []) if "sun" in str(x.get("name","")).lower()]
nm=suns[0].get("name") if suns else "Sun1"
rc("set_light_properties",{"name":nm,"intensity":95000,"color":{"r":1,"g":0.97,"b":0.9},"shadows_enabled":True},15)
rc("set_rotation",{"name":nm,"x":48,"y":-32,"z":0},12)
rc("setup_hdrp_volume",{"fog":True,"fog_distance":700.0,"exposure_mode":"Fixed","fixed_exposure":13.8},20)
# kamp + kale ortasindan establishing acilar
cf=pos_of("Campfire") or (-526,142,-98)
kp=pos_of("GothicCastle") or (-516,142,-168)
mx,mz=(cf[0]+kp[0])/2,(cf[2]+kp[2])/2
yaw0=math.degrees(math.atan2(kp[0]-cf[0], kp[2]-cf[2]))
from ap import _studio_shot
DST="C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject/AutopilotData/screenshots"
shots=[]
i=0
for size in [60,110,180]:
    for pit in [6,18,32]:
        for dyaw in [-40,0,40,90]:
            rc("set_scene_view",{"pivot_x":mx,"pivot_y":cf[1]+size*0.12,"pivot_z":mz,
               "size":size,"pitch":pit,"yaw":yaw0+dyaw},25)
            time.sleep(0.4)
            r=_studio_shot(name=f"fresh_{i:03d}")
            src=(r or {}).get("source","")
            if src and os.path.exists(src):
                shutil.copy(src, f"studio/autopilot/_fresh/f{i:03d}.png")
            i+=1
            if i%12==0: fresh()
Path("studio/autopilot/_fc2.txt").write_text(json.dumps({"cekilen":i}), encoding="utf-8")
print("FRESHCAP_DONE", i)
