import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
cf=pos_of("Campfire") or (-526,141,-98)
rc("set_scene_view", {"pivot_x":cf[0],"pivot_y":cf[1]+10,"pivot_z":cf[2],"size":70,"pitch":6,"yaw":200}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="RESULT")
Path("studio/autopilot/_result.txt").write_text((r or {}).get("source",""), encoding="utf-8")
