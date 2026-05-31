import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_cs2.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
d = rc("get_object_details", {"name":"GothicCastle"}, 15) or {}
if d.get("name"):
    p=d.get("position",{}); s=d.get("scale",{}); r=d.get("rotation",{})
    out.append(f"VAR pos=({p.get('x',0):.0f},{p.get('y',0):.0f},{p.get('z',0):.0f}) scale={s.get('x',0):.1f} rotX={r.get('x',0):.0f} child={d.get('child_count')}")
    kx=float(p.get('x',-482)); ky=float(p.get('y',95)); kz=float(p.get('z',-311))
else:
    out.append("YOK"); kx,ky,kz=-482,95,-311
# net kare
rc("set_scene_view", {"target":"GothicCastle","pitch":8,"yaw":220}, 30)
time.sleep(1.3)
from ap import _studio_shot
_studio_shot(name="castle_now")
out.append("shot=castle_now")
Path("studio/autopilot/_cs2.txt").write_text("\n".join(out), encoding="utf-8")
