import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
es=rc("get_editor_state",{},15) or {}
out={"play_oncesi":es.get("is_playing")}
if es.get("is_playing"):
    rc("play_mode",{"play":False},40); time.sleep(3); fresh()
es2=rc("get_editor_state",{},15) or {}
out["play_sonrasi"]=es2.get("is_playing")
guard_scene()
out["forest"]=child_count("WorldForestGLB")
Path("studio/autopilot/_sp.txt").write_text(json.dumps(out), encoding="utf-8")
