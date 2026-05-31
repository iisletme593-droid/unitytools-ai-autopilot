"""Isik huzmeleri (LightBeam/DivineBeam/DivineWisp) kamp ustunde (XZ -526,-98)
kalmis -> kaleye tasi (-482,-311). DivineSpot da. Kamp temizlenir, kale isiklanir."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

KX, KZ = -482.5, -311.5
ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

log = []
ksurf = ap.surf(KX, KZ, 96)  # kale zemini ~96.5
log.append(f"kale_zemin={ksurf:.1f}")

# her huzme objesini kale XZ'sine + uygun Y'ye tasi
moves = {
    "LightBeam":  ksurf + 110,
    "DivineBeam": ksurf + 90,
    "DivineWisp": ksurf + 95,
    "DivineSpot": ksurf + 210,
}
for nm, y in moves.items():
    d = ap.rc("get_object_details", {"name": nm}, 12) or {}
    if not d.get("name"):
        log.append(f"{nm}: YOK"); continue
    ap.rc("set_position", {"name": nm, "x": KX, "y": y, "z": KZ}, 15)
    log.append(f"{nm} -> ({KX},{y:.0f},{KZ})")

ap.save()
# dogrula: find ile yeni konumlar
r = ap.rc("find_scene_objects", {"name_contains": "Divine", "max_count": 6}, 20) or {}
chk = []
for o in (r.get("objects") or []):
    p = o.get("position") or {}
    chk.append([o.get("name", "?"), round(p.get("x", 0), 0), round(p.get("y", 0), 0), round(p.get("z", 0), 0)])
r2 = ap.rc("find_scene_objects", {"name_contains": "LightBeam", "max_count": 3}, 20) or {}
for o in (r2.get("objects") or []):
    p = o.get("position") or {}
    chk.append([o.get("name", "?"), round(p.get("x", 0), 0), round(p.get("y", 0), 0), round(p.get("z", 0), 0)])
log.append("YENI=" + json.dumps(chk, ensure_ascii=False))
log.append("FIXBEAMS_DONE")
Path("studio/autopilot/_fixbeams.txt").write_text("\n".join(log), encoding="utf-8")
print("FIXBEAMS_DONE")
