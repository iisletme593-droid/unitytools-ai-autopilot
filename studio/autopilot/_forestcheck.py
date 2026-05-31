import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
res={}
d=rc("get_object_details",{"name":"WorldForestGLB"},15) or {}
res["forest_child"]=d.get("child_count")
# Tree_ isimli kac obje var?
r=rc("find_scene_objects",{"name_contains":"Tree_","max_count":50},40) or {}
res["tree_count_field"]=r.get("count")
res["tree_returned"]=len(r.get("objects") or [])
Path("studio/autopilot/_fc.txt").write_text(json.dumps(res), encoding="utf-8")
