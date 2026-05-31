import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
fr = rc("set_scene_view", {"target":"WoodHouse","pitch":5,"yaw":200}, 30)
out={"bounds": fr.get("size") if isinstance(fr,dict) else "?"}
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="houseZoom")
out["path"]=(r or {}).get("path")
Path("studio/autopilot/_hs.txt").write_text(json.dumps(out), encoding="utf-8")
