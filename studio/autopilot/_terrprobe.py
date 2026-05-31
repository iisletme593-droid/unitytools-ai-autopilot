import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
gc = ap.rc("get_object_details", {"name": "GothicCastle"}, 12) or {}
p = gc.get("position") or {}
cx, cz = p.get("x", -482), p.get("z", -311)
res = {"castle_pos": [round(cx,1), round(p.get("y",0),1), round(cz,1)]}
# kaleden cesitli uzakliklarda terrain (kale geometrisi disinda)
samples = {}
for tag, dx, dz in [("center",0,0),("e40",40,0),("w40",-40,0),("n40",0,40),
                    ("s40",0,-40),("e70",70,0),("ne55",40,40)]:
    y = ap.surf(cx+dx, cz+dz, 142)
    samples[tag] = round(y, 1)
res["terrain_samples"] = samples
res["terrain_disinda_ortalama"] = round(
    sum(v for k,v in samples.items() if k != "center") / (len(samples)-1), 1)
Path("studio/autopilot/_terrprobe.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("PROBE_DONE")
