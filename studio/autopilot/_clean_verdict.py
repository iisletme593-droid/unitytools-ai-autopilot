import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
# single clean refresh; do NOT import_asset (that races with Unity's auto-import
# and caused the 'used by another process' errors). Let Unity compile.
rc("execute_menu_item", {"path": "Assets/Refresh"}, 30)
time.sleep(10); fresh()
for _ in range(16):
    es = rc("get_editor_state", {}, 20) or {}
    if not es.get("is_compiling") and not es.get("is_updating"): break
    time.sleep(3); fresh()
# mark a boundary token time so check_compile scans only fresh output
Path("studio/autopilot/_verdict.txt").write_text("refresh-done", encoding="utf-8")
