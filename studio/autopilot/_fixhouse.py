import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# WoodHouse FBX Z-up -> Unity import zaten ceviriyor; rotX 270 yatik -> 0 dene
rc("set_rotation", {"name":"WoodHouse","x":0,"y":0,"z":0}, 12)
d=rc("get_object_details",{"name":"WoodHouse"},12) or {}
p=d.get("position") or {}; cx=float(p.get("x",-510)); cz=float(p.get("z",-95))
sy=surf(cx,cz,139); rc("set_position",{"name":"WoodHouse","x":cx,"y":sy-0.2,"z":cz},12)
save()
d2=rc("get_object_details",{"name":"WoodHouse"},12) or {}
r2=d2.get("rotation") or {}; p2=d2.get("position") or {}
Path("studio/autopilot/_fh.txt").write_text(
    json.dumps({"rotX":round(float(r2.get("x",0)),0),"y":round(float(p2.get("y",0)),1),"ground":round(sy,1)}),
    encoding="utf-8")
