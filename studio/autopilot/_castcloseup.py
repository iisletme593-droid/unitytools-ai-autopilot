import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
d = rc("get_object_details", {"name":"GothicCastle"}, 15) or {}
p=d.get("position",{}); s=d.get("scale",{})
out=[f"pos=({p.get('x',0):.0f},{p.get('y',0):.0f},{p.get('z',0):.0f}) scale={s.get('x',0):.2f}"]
fr = rc("set_scene_view", {"target":"GothicCastle","pitch":6,"yaw":210}, 30)
out.append("bounds_size="+str(fr.get("size") if isinstance(fr,dict) else "?"))
time.sleep(1.5)
from ap import _studio_shot
r=_studio_shot(name="cast_closeup")
out.append("shot="+str((r or {}).get("path","?")))
Path("studio/autopilot/_cc2.txt").write_text("\n".join(out), encoding="utf-8")
