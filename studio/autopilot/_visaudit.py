import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# kale + ev konumlari
for nm in ["GothicCastle","WoodHouse","CampSite"]:
    p=pos_of(nm); out.append(f"{nm}={p}")
# kale yakindan
kp = pos_of("GothicCastle") or (-604,97,-150)
shot("audit_castle", kp[0]+45, kp[1]+25, kp[2]+45, 90, 8, 220)
# ev yakindan
wp = pos_of("WoodHouse") or (-533,138,-105)
shot("audit_house", wp[0]+14, wp[1]+6, wp[2]+14, 22, 4, 210)
# zemin yakindan (kamp onu)
cf = pos_of("Campfire") or wp
shot("audit_ground", cf[0]+6, cf[1]+4, cf[2]+6, 16, 28, 40)
out.append("shots: audit_castle/house/ground")
# terrain layer bilgisi
ti = rc("list_terrains", {}, 20) or {}
ts = ti.get("terrains") or []
out.append("terrain="+json.dumps(ts[0] if ts else {})[:200])
Path("studio/autopilot/_visaudit.txt").write_text("\n".join(out), encoding="utf-8")
