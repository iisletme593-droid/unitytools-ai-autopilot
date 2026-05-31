import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# SolidFir diskte var mi?
import os
PROJ="C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject"
out.append("SolidFir.glb_unity="+str(os.path.exists(PROJ+"/Assets/Art/HQ/SolidFir.glb")))
out.append("SolidFir.fbx_studio="+str(os.path.exists("studio/assets/hq/SolidFir/final.fbx")))
out.append("LP_Fir_GLB="+str(os.path.exists(PROJ+"/Assets/Art/HQ/LP_Fir_GLB.glb")))
# kamp yaninda bir test agaci: LP_Fir_GLB (alpha yok, koyu) dene
cf=pos_of("Campfire") or (-526,141,-98)
for _ in range(2): rc("delete_object",{"name":"TreeTest"},8)
r=place_pinned("Assets/Art/HQ/LP_Fir_GLB.glb", cf[0]+12, cf[2]+12, 8.0, "TreeTest",
               glb=True, rot_y=0, y_offset=-0.2, min_surface_y=5.0, max_slope_deg=40.0)
out.append("place_LPFir="+("ok" if r else "FAIL"))
save()
# yakin kare
d=rc("get_object_details",{"name":"TreeTest"},12) or {}
p=d.get("position") or {}; tx=float(p.get("x",cf[0]+12)); ty=float(p.get("y",cf[1])); tz=float(p.get("z",cf[2]+12))
rc("set_scene_view", {"pivot_x":tx,"pivot_y":ty+4,"pivot_z":tz,"size":12,"pitch":3,"yaw":40}, 30)
time.sleep(1.5)
from ap import _studio_shot
sr=_studio_shot(name="treetest")
out.append("shot="+(sr or {}).get("source",""))
Path("studio/autopilot/_tt.txt").write_text("\n".join(out), encoding="utf-8")
