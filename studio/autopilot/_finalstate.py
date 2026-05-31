import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
res={}
for nm in ["GothicCastle","WoodHouse","WorldForestGLB","CampSite","SK_Hero"]:
    d=rc("get_object_details",{"name":nm},12) or {}
    if d.get("name"):
        p=d.get("position") or {}; r=d.get("rotation") or {}; s=d.get("scale") or {}
        res[nm]={"pos":[round(float(p.get(k,0)),0) for k in("x","y","z")],
                 "rotX":round(float(r.get("x",0)),0),"scale":round(float(s.get("x",0)),1),
                 "child":d.get("child_count")}
    else: res[nm]="YOK"
cm=rc("get_material_properties",{"name":"GothicCastle"},15) or {}
res["castle_mat"]={"mat":cm.get("material"),"shader":cm.get("shader")}
# terrain layers
ti=rc("list_terrains",{},15) or {}; ts=(ti.get("terrains") or [{}])[0]
res["terrain_layers"]=ts.get("layers")
Path("studio/autopilot/_finalstate.txt").write_text(json.dumps(res,indent=1), encoding="utf-8")
