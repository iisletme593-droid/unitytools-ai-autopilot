import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); time.sleep(1); fresh(); guard_scene()
out={}
out["forest_once"]=child_count("WorldForestGLB")
r=rc("save_scene",{},60)
out["save"]=r if isinstance(r,dict) else str(r)
time.sleep(1)
out["forest_sonra"]=child_count("WorldForestGLB")
Path("studio/autopilot/_sn.txt").write_text(json.dumps(out), encoding="utf-8")
