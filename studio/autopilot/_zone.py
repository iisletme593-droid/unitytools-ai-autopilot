import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out={}
for nm in ["Campfire","WoodHouse","GothicCastle","CampSite"]:
    out[nm]=pos_of(nm)
# bu bolgede kac agac var (kamp 80m yaricap)
cf=pos_of("Campfire") or (-526,142,-98)
import math
r=rc("find_scene_objects",{"name_contains":"Tree_","max_count":2000},90) or {}
near=0
for o in (r.get("objects") or []):
    if not isinstance(o,dict) or "Tree_" not in str(o.get("name","")): continue
    p=o.get("position") or {}
    if p.get("x") is None: continue
    if math.hypot(float(p["x"])-cf[0], float(p["z"])-cf[2])<80: near+=1
out["kamp_80m_agac"]=near
out["toplam_agac"]=r.get("count")
Path("studio/autopilot/_zone.txt").write_text(json.dumps(out), encoding="utf-8")
