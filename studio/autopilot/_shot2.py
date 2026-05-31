import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
d=rc("get_object_details",{"name":"GothicCastle"},12) or {}
p=d.get("position") or {}; cx=float(p.get("x",-482)); cy=float(p.get("y",94)); cz=float(p.get("z",-311))
# yuksekten, tepeden bakis (agac ustu)
rc("set_scene_view", {"pivot_x":cx,"pivot_y":cy+60,"pivot_z":cz,"size":120,"pitch":35,"yaw":210}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="castTop")
Path("studio/autopilot/_shot2.txt").write_text(json.dumps(r), encoding="utf-8")
