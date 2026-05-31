import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
d = rc("get_object_details", {"name":"GothicCastle"}, 15) or {}
p=d.get("position") or {}; r=d.get("rotation") or {}; s=d.get("scale") or {}
res={"pos_y":round(float(p.get("y",0)),1),
     "rotX":round(float(r.get("x",0)),0),
     "scale":round(float(s.get("x",0)),2),
     "child":d.get("child_count")}
Path("studio/autopilot/_cc3.txt").write_text(json.dumps(res), encoding="utf-8")
