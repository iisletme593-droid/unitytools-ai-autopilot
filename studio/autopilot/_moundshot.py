import sys, time, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
cf = ap.pos_of("Campfire") or (-526, 142, -98)
out = {}
# yakindan tan-mound incele
ap.rc("set_scene_view", {"pivot_x": cf[0]+10, "pivot_y": cf[1], "pivot_z": cf[2]+10,
                          "size": 7, "pitch": 12, "yaw": 130}, 25)
time.sleep(1.4)
r = ap._studio_shot(name="mound_cu") or {}
out["mound"] = str(Path(os.getcwd()) / r.get("path", ""))
# olasi rock/prop gruplarini sorgula
for nm in ("WorldRocks", "Rocks", "RockField", "CampRocks", "Boulders", "CampSite",
           "CampProps", "Cliffs", "RockCliffs", "CampForest", "WorldGrass"):
    d = ap.rc("get_object_details", {"name": nm}, 12) or {}
    if d.get("name"):
        p = d.get("position") or {}
        out[nm] = {"child": d.get("child_count"),
                   "pos": [round(p.get("x",0),0), round(p.get("y",0),0), round(p.get("z",0),0)]}
Path("studio/autopilot/_mound.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print("MOUND_DONE " + out["mound"])
