"""GUVENILIR kale durumu: get_object_details bu turda araliklarla BOS donuyor
(zero bounds). Gercek veri gelene kadar RETRY. job_lift_castle bos-veriyle
calismis olabilir -> kaleyi ucurmus olabilir. Once gercegi ogren."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()

def solid_details(name, tries=8):
    for i in range(tries):
        d = ap.rc("get_object_details", {"name": name}, 18) or {}
        pos = d.get("position") or {}
        wb = d.get("world_bounds") or {}
        s = wb.get("size") or {}
        # gercek veri: position.y veya bounds.y anlamli
        if d.get("name") and (abs(pos.get("y", 0)) > 0.01 or s.get("y", 0) > 0.5):
            return d, i
        time.sleep(1.0); ap.fresh()
    return (ap.rc("get_object_details", {"name": name}, 18) or {}), tries

res = {}
for nm in ("GothicCastle", "CastleSpires", "T_Keep_shaft", "Campfire"):
    d, tries = solid_details(nm)
    pos = d.get("position") or {}
    wb = d.get("world_bounds") or {}; c = wb.get("center") or {}; s = wb.get("size") or {}
    res[nm] = {
        "var_mi": bool(d.get("name")),
        "pos": [round(pos.get("x", -999), 1), round(pos.get("y", -999), 1), round(pos.get("z", -999), 1)],
        "bbox": [round(s.get("x", 0), 1), round(s.get("y", 0), 1), round(s.get("z", 0), 1)],
        "taban_y": round(c.get("y", 0) - s.get("y", 0)/2, 1) if s.get("y") else None,
        "retry": tries,
    }
# kale konumunda gercek zemin
gp = res["GothicCastle"]["pos"]
if gp[0] > -900:
    res["zemin_kalede"] = round(ap.surf(gp[0], gp[2], 100), 1)
Path("studio/autopilot/_castle_truth.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
print("TRUTH_DONE")
