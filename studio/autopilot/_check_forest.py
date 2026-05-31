import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); time.sleep(2); fresh(); guard_scene()
out={"forest":child_count("WorldForestGLB")}
out["scene"]=(rc("list_scenes",{},15) or {}).get("active_scene")
Path("studio/autopilot/_cf.txt").write_text(json.dumps(out), encoding="utf-8")
