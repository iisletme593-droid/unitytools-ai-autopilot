import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out={}
# WorldForestGLB'nin kendi transform pozisyonu
d=rc("get_object_details",{"name":"WorldForestGLB"},15) or {}
out["forest_pos"]=d.get("position")
out["forest_child"]=d.get("child_count")
# get_object_details cocuk isimlerini veriyor mu?
out["has_children_field"]= "children" in d
if "children" in d:
    ch=d.get("children") or []
    out["ilk_cocuklar"]=[c if isinstance(c,str) else c.get("name") for c in ch[:5]]
Path("studio/autopilot/_fp.txt").write_text(json.dumps(out,ensure_ascii=False), encoding="utf-8")
