import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
rc("set_rotation", {"name":"GothicCastle","x":0,"y":0,"z":0}, 12)
d=rc("get_object_details",{"name":"GothicCastle"},12) or {}
p=d.get("position") or {}; cx=float(p.get("x",-482)); cz=float(p.get("z",-311))
sy=surf(cx,cz,95); rc("set_position",{"name":"GothicCastle","x":cx,"y":sy-2.0,"z":cz},12)
save()
d2=rc("get_object_details",{"name":"GothicCastle"},12) or {}
r2=d2.get("rotation") or {}
Path("studio/autopilot/_fixrot.txt").write_text(
    json.dumps({"rotX":round(float(r2.get("x",0)),0),"y":round(float((d2.get("position") or {}).get("y",0)),1),"ground":round(sy,1)}),
    encoding="utf-8")
