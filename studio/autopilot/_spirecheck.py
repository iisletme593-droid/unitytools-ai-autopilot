import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
res = {}
for nm in ("GothicCastle", "CastleSpires", "T_Keep_shaft"):
    d = ap.rc("get_object_details", {"name": nm}, 18) or {}
    wb = d.get("world_bounds") or {}; c = wb.get("center", {}); s = wb.get("size", {})
    res[nm] = {"center_y": round(c.get("y", 0), 1),
               "size": [round(s.get("x",0),1), round(s.get("y",0),1), round(s.get("z",0),1)],
               "base_y": round(c.get("y",0) - s.get("y",0)/2, 1),
               "top_y": round(c.get("y",0) + s.get("y",0)/2, 1)}
# terrain at castle
cx = res["GothicCastle"]["center_y"]
gc = ap.rc("get_object_details", {"name": "GothicCastle"}, 12) or {}
p = gc.get("position") or {}
res["terrain_y_at_castle"] = round(ap.surf(p.get("x", -482), p.get("z", -311), 142), 1)
# combined silhouette ratio (castle + spires)
cb = res["GothicCastle"]; sb = res["CastleSpires"]
combo_top = max(cb["top_y"], sb["top_y"]); combo_base = min(cb["base_y"], sb["base_y"])
foot = max(cb["size"][0], cb["size"][2], sb["size"][0], sb["size"][2])
res["SILUET"] = {"toplam_yukseklik": round(combo_top - combo_base, 1),
                 "ayak": round(foot, 1),
                 "oran": round((combo_top - combo_base) / max(foot, 1), 2),
                 "tepe_y": round(combo_top, 1)}
Path("studio/autopilot/_spirecheck.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("CHECK_DONE")
