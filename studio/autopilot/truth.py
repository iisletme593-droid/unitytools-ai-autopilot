"""GROUND TRUTH — yalniz GUVENILIR yollar: find_scene_objects (transform) +
surf (zemin) + get_atmosphere_state. get_object_details bounds KULLANMA.
Cikti JSON. Hicbir tahmin yok."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
playing = es.get("is_playing")
if playing:
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

rep = {"was_playing": playing}

def find(q, n=12):
    r = ap.rc("find_scene_objects", {"name_contains": q, "max_count": n}, 20) or {}
    out = []
    for o in (r.get("objects") or []):
        p = o.get("position") or {}
        out.append([o.get("name", "?")[:20], round(p.get("x",0),1), round(p.get("y",0),1), round(p.get("z",0),1)])
    return out

rep["GothicCastle"] = find("GothicCastle", 3)
rep["spire_kalintilari"] = find("_shaft", 12) + find("_roof", 12) + find("CastleSpires", 3)
rep["DivineBeam"] = find("DivineBeam", 3)
rep["Campfire"] = find("Campfire", 3)
rep["SK_Hero"] = find("SK_Hero", 2)
rep["WoodHouse"] = find("WoodHouse", 4)

# sayim (find ile ust-obje sayisi)
for grp in ("VegGrass", "FernUndergrowth"):
    r = ap.rc("find_scene_objects", {"name_contains": grp, "max_count": 999}, 25) or {}
    rep[grp + "_count"] = len(r.get("objects") or [])

# atmosfer
atm = ap.rc("get_atmosphere_state", {}, 15) or {}
rep["atmosfer"] = {k: atm.get(k) for k in ("fog_enabled","fog_color_r","fog_color_g",
                   "fog_color_b","skybox_shader","ambient_intensity")}

# kale zemini
gc = rep["GothicCastle"]
if gc:
    _, x, y, z = gc[0]
    rep["castle_zemin"] = round(ap.surf(x, z, y), 1)
    rep["castle_pivot_y"] = y

Path("studio/autopilot/truth.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
print("TRUTH_DONE")
