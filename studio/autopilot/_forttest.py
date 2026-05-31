import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
FORT="Assets/FantasyRPG/Models/PolyHaven/Environment/Structures/Environment_Structures_03_ModularFort.glb"
kp = pos_of("GothicCastle") or (-482,95,-311)
# test objesi olarak koy (kaleyi henuz silme)
for _ in range(2): rc("delete_object", {"name":"FortTest"}, 10)
r = rc("place_asset_on_terrain", {"asset_path":FORT,"x":kp[0],"z":kp[2],"scale":1.0,
    "name":"FortTest","min_surface_y":0.0,"max_slope_deg":89.0,"search_radius":0.0,"y_offset":0.0}, 90)
out.append("place="+json.dumps(r)[:120])
rc("set_rotation", {"name":"FortTest","x":0,"y":0,"z":0}, 12)
# bounds olc (target ile auto-frame size'i bounds verir)
fr = rc("set_scene_view", {"target":"FortTest","pitch":8,"yaw":35}, 30)
out.append("bounds_size="+str(fr.get("size") if isinstance(fr,dict) else "?"))
import time as _t; _t.sleep(1)
from ap import _studio_shot
print(_studio_shot(name="fort_test"))
out.append("shot=fort_test")
Path("studio/autopilot/_ft.txt").write_text("\n".join(out), encoding="utf-8")
