import sys, time, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
cf = ap.pos_of("Campfire") or (-526, 142, -98)
out = []
for name, pitch, size in [("BIRD_down", 89, 50), ("HORIZON_flat", 2, 50)]:
    r1 = ap.rc("set_scene_view", {"pivot_x": cf[0], "pivot_y": cf[1], "pivot_z": cf[2],
                                   "size": size, "pitch": pitch, "yaw": 0}, 25)
    time.sleep(1.5)
    r = ap._studio_shot(name=name) or {}
    p = r.get("path", "")
    ab = str(Path(os.getcwd()) / p) if p and not os.path.isabs(p) else p
    out.append(f"{name}\tsetview_ok={bool(r1)}\t{ab}")
Path("studio/autopilot/_camtest.txt").write_text("\n".join(out), encoding="utf-8")
print("CAMTEST_OK")
