import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
cf=pos_of("Campfire") or (-526,142,-98)
rc("set_scene_view", {"pivot_x":cf[0],"pivot_y":cf[1]+15,"pivot_z":cf[2],"size":110,"pitch":10,"yaw":200}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="STATE")
Path("studio/autopilot/_sf.txt").write_text((r or {}).get("source",""), encoding="utf-8")
