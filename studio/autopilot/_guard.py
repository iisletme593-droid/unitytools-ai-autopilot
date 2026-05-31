import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
ok = guard_scene()
s = rc("list_scenes", {}, 15) or {}
Path("studio/autopilot/_guard.txt").write_text(
    f"guard={ok} scene={s.get('active_scene')} "
    f"resnodes={child_count('ResourceNodes')} craft={'OK' if pos_of('CraftStation') else 'YOK'}",
    encoding="utf-8")
