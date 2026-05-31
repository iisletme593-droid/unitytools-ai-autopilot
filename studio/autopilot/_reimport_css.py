import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
PROJ = "C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject"
base = "FantasyRPG/Scripts/UI/Gameplay"
out = {}
# import the recreated file so Unity picks it up + recompiles
src = f"{PROJ}/Assets/{base}/CharacterSelectScreen.cs"
out["imp"] = rc("import_asset", {"src_path": src, "dst_relative": f"{base}/CharacterSelectScreen.cs"}, 60)
rc("execute_menu_item", {"path": "Assets/Refresh"}, 30)
time.sleep(8); fresh()
for _ in range(14):
    es = rc("get_editor_state", {}, 20) or {}
    if not es.get("is_compiling") and not es.get("is_updating"):
        out["final"] = es; break
    time.sleep(3); fresh()
Path("studio/autopilot/_reimp.txt").write_text(json.dumps(out)[:400], encoding="utf-8")
