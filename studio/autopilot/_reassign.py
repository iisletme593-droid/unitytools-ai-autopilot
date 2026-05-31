import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_ra.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
rc("execute_menu_item", {"path":"Assets/Refresh"}, 30); time.sleep(6); fresh()
am = rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_CastleStone.mat",
    "name_contains":"GothicCastle","recurse":True}, 60)
out.append("assign="+json.dumps(am)[:140])
out.append("saved="+str(save()))
Path("studio/autopilot/_ra.txt").write_text("\n".join(out), encoding="utf-8")
