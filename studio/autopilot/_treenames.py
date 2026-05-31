import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out={}
# WorldForestGLB cocuklarinin gercek isimleri ne?
d=rc("get_object_details",{"name":"WorldForestGLB"},15) or {}
out["forest_child"]=d.get("child_count")
# cesitli prefix dene
for pre in ["Tree_","CardFir","Fir","Conifer","Pine","tree","GLB_","Tree"]:
    r=rc("find_scene_objects",{"name_contains":pre,"max_count":5},30) or {}
    out[pre]=r.get("count")
# list_scene_objects ile WorldForestGLB altindan ornek isim
ls=rc("list_scene_objects",{"root":"WorldForestGLB","max_count":8},30) or {}
objs=ls.get("objects") or []
out["ornek_isimler"]=[o.get("name") for o in objs[:8] if isinstance(o,dict)]
Path("studio/autopilot/_tn.txt").write_text(json.dumps(out), encoding="utf-8")
