import sys, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
rc("set_rotation", {"name":"GothicCastle","x":0,"y":0,"z":0}, 12)
# tabani araziye otur
d=rc("get_object_details",{"name":"GothicCastle"},12) or {}
p=d.get("position") or {}; cx=float(p.get("x",-482)); cz=float(p.get("z",-311))
sy=surf(cx,cz,95); rc("set_position",{"name":"GothicCastle","x":cx,"y":sy-1.0,"z":cz},12)
save()
rc("set_scene_view", {"target":"GothicCastle","pitch":8,"yaw":210}, 30); time.sleep(1.4)
from ap import _studio_shot
_studio_shot(name="rot0")
