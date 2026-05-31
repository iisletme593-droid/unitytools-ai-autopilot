import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
mp = rc("get_material_properties", {"name":"WoodHouse"}, 20) or {}
Path("studio/autopilot/_hm2.txt").write_text(json.dumps(mp), encoding="utf-8")
