import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
rc("execute_menu_item", {"path":"Assets/Refresh"}, 30)
time.sleep(6); fresh()
# poll until not compiling
for _ in range(10):
    es = rc("get_editor_state", {}, 20) or {}
    if not es.get("is_compiling") and not es.get("is_updating"):
        print("STATE", json.dumps(es)); break
    time.sleep(3); fresh()
guard_scene()
s = rc("list_scenes", {}, 15) or {}
print("SCENE", s.get("active_scene"))
