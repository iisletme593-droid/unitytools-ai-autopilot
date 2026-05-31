import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
for nm in ["SK_Hero","TI_Playable","TI_HUD","TI_Minimap","TI_DayCycleManager","Main Camera"]:
    d=rc("get_object_details",{"name":nm},12) or {}
    if d.get("name"):
        comps=d.get("components") or []
        out.append(f"{nm}: {len(comps)} comp -> {','.join(comps[:6])}")
    else:
        out.append(f"{nm}: YOK")
out.append("forest="+str(child_count("WorldForestGLB")))
out.append("saved="+str(save()))
Path("studio/autopilot/_postwire.txt").write_text("\n".join(out), encoding="utf-8")
