import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out={}
for nm in ["WorldForestGLB","GothicCastle","WoodHouse","CampSite","Campfire","SK_Hero","CampForest","WorldGrass","TI_Playable"]:
    d=rc("get_object_details",{"name":nm},12) or {}
    if d.get("name"):
        p=d.get("position") or {}
        out[nm]={"var":True,"pos":[round(float(p.get(k,0))) for k in("x","y","z")],"child":d.get("child_count")}
    else:
        out[nm]={"var":False}
Path("studio/autopilot/_t2.txt").write_text(json.dumps(out,ensure_ascii=False), encoding="utf-8")
