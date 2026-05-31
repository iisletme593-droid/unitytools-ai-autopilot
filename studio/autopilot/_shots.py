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
ks = ap.pos_of("GothicCastle") or (-482, 146, -311)
views = [
    ("grass_eye",  cf[0]+6,  cf[1]+1.6, cf[2]+6,  10, 8,  50),   # cim goz hizasi yakin
    ("camp_wide",  cf[0],    cf[1]+6,   cf[2],    45, 12, 210),  # kamp establishing
    ("castle_dir", (cf[0]+ks[0])/2, ks[1]+8, (cf[2]+ks[2])/2, 160, 11, 25),  # kaleye dogru
]
lines = []
for name, px, py, pz, size, pitch, yaw in views:
    ap.rc("set_scene_view", {"pivot_x": px, "pivot_y": py, "pivot_z": pz,
                              "size": size, "pitch": pitch, "yaw": yaw}, 25)
    time.sleep(1.4)
    r = ap._studio_shot(name=name) or {}
    p = r.get("path", "")
    ab = str(Path(os.getcwd()) / p) if p and not os.path.isabs(p) else p
    lines.append(f"{name}\t{ab}")
Path("studio/autopilot/_shots.txt").write_text("\n".join(lines), encoding="utf-8")
print("SHOTS_OK")
for l in lines: print(l)
