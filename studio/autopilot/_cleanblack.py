import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# siyah-blok CardFir kamp agaclarini sil (CampForest grubu)
before=child_count("CampForest")
out.append("campforest_once="+str(before))
for _ in range(3):
    r=rc("delete_object",{"name":"CampForest"},12)
    if not (isinstance(r,dict) and r.get("ok")): break
out.append("campforest_sonra="+str(child_count("CampForest")))
out.append("test_agac_sil="+json.dumps(rc("delete_object",{"name":"TreeTest"},10))[:40])
out.append("forest_intact="+str(child_count("WorldForestGLB")))
out.append("saved="+str(save()))
Path("studio/autopilot/_cb.txt").write_text("\n".join(out), encoding="utf-8")
