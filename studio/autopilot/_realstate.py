import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out={}
for nm in ["WorldForestGLB","WoodHouse","GothicCastle","Campfire","SK_Hero","CampSite","CampForest"]:
    p=pos_of(nm); out[nm]={"var":bool(p),"pos":[round(v) for v in p] if p else None}
out["forest_child"]=child_count("WorldForestGLB")
out["es"]=rc("get_editor_state",{},15)
Path("studio/autopilot/_rs.txt").write_text(json.dumps(out,ensure_ascii=False), encoding="utf-8")
