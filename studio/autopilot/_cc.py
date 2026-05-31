import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
rc("execute_menu_item", {"path":"Assets/Refresh"}, 30)
time.sleep(7); fresh()
es={}
for _ in range(8):
    es = rc("get_editor_state", {}, 20) or {}
    if not es.get("is_compiling") and not es.get("is_updating"): break
    time.sleep(3); fresh()
guard_scene()
s = rc("list_scenes", {}, 15) or {}
Path("studio/autopilot/_cc.txt").write_text(
    f"COMPILING={es.get('is_compiling')} SCENE={s.get('active_scene')}", encoding="utf-8")
