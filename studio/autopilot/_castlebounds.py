import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
d = ap.rc("get_object_details", {"name": "GothicCastle"}, 20) or {}
wb = d.get("world_bounds") or {}
s = wb.get("size", {}); c = wb.get("center", {})
sx, sy, sz = s.get("x", 0), s.get("y", 0), s.get("z", 0)
foot = max(sx, sz)
res = {
    "size": [round(sx, 1), round(sy, 1), round(sz, 1)],
    "footprint": round(foot, 1),
    "height": round(sy, 1),
    "yukseklik_taban_orani": round(sy / max(foot, 1), 2),  # gotik: >1 ideal, bodur: <0.5
    "center": [round(c.get("x", 0), 1), round(c.get("y", 0), 1), round(c.get("z", 0), 1)],
    "child_count": d.get("child_count"),
}
Path("studio/autopilot/_castlebounds.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("BOUNDS_DONE ratio=" + str(res["yukseklik_taban_orani"]))
