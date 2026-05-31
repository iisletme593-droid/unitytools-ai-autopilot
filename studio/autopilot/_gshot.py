import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
cf = ap.pos_of("Campfire") or (-526, 142, -98)
ap.rc("set_scene_view", {"pivot_x": cf[0] + 8, "pivot_y": cf[1] + 2, "pivot_z": cf[2] + 8,
                          "size": 14, "pitch": 6, "yaw": 50}, 25)
time.sleep(1.5)
r = ap._studio_shot(name="grasscheck") or {}
Path("studio/autopilot/_gpath.txt").write_text(json.dumps(r, default=str), encoding="utf-8")
print("SHOT_DONE")
