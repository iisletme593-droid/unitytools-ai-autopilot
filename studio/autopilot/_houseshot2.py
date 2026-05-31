import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
rc("set_scene_view", {"target":"WoodHouse","pitch":5,"yaw":200}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="houseFixed")
Path("studio/autopilot/_hf2.txt").write_text(json.dumps(r), encoding="utf-8")
