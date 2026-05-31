import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# 48m -> ~12m hedef: scale 3.0 * (12/48) = 0.75
rc("set_scale", {"name":"WoodHouse","x":0.75,"y":0.75,"z":0.75}, 12)
d=rc("get_object_details",{"name":"WoodHouse"},12) or {}
p=d.get("position") or {}; cx=float(p.get("x",-510)); cz=float(p.get("z",-88))
sy=surf(cx,cz,135); rc("set_position",{"name":"WoodHouse","x":cx,"y":sy-0.1,"z":cz},12)
save()
fr=rc("set_scene_view",{"target":"WoodHouse","pitch":5,"yaw":200},30)
Path("studio/autopilot/_hsc.txt").write_text(json.dumps({"yeni_bounds":fr.get("size") if isinstance(fr,dict) else "?"}), encoding="utf-8")
