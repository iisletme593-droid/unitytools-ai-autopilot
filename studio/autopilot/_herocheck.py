import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
for nm in ["SK_Hero","Player","Player_NordWarrior"]:
    d=rc("get_object_details",{"name":nm},15) or {}
    if d.get("name"):
        out.append(f"{nm}: pos={d.get('position')} tag={d.get('tag')} comps={d.get('components')}")
    else:
        out.append(f"{nm}: YOK")
# tag'i Player olan var mi?
r=rc("find_scene_objects",{"name_contains":"Hero","max_count":10},30) or {}
out.append("Hero-isimli: "+",".join(o.get("name","") for o in (r.get("objects") or []) if isinstance(o,dict)))
Path("studio/autopilot/_hero.txt").write_text("\n".join(out), encoding="utf-8")
