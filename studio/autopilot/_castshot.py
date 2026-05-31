import sys, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
rc("set_scene_view", {"target":"GothicCastle","pitch":9,"yaw":220}, 30)
time.sleep(1.5)
from ap import _studio_shot
r = _studio_shot(name="castle_final_check")
Path("studio/autopilot/_castshot.txt").write_text(str((r or {}).get("path","?")), encoding="utf-8")
