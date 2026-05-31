import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
PROJ = "C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject"
base = "FantasyRPG/Scripts/UI/Gameplay"
out = {}
# reimport the two files that REFERENCE CharacterSelectScreen -> forces real recompile
for f in ["StarterLoadout.cs", "PauseMenu.cs"]:
    out[f] = bool(rc("import_asset", {"src_path": f"{PROJ}/Assets/{base}/{f}",
                                      "dst_relative": f"{base}/{f}"}, 60))
rc("execute_menu_item", {"path": "Assets/Refresh"}, 30)
time.sleep(10); fresh()
for _ in range(16):
    es = rc("get_editor_state", {}, 20) or {}
    if not es.get("is_compiling") and not es.get("is_updating"):
        out["final"] = es; break
    time.sleep(3); fresh()
Path("studio/autopilot/_ff.txt").write_text(json.dumps(out)[:300], encoding="utf-8")
