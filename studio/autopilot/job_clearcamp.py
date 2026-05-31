"""Kamp temizligi: CampForest (kamp uzerine bindirilmis 57 dusuk-kalite CardFir
= beyaz shard + buyume) SIL. Iyi orman WorldForestGLB (1736) kalir.
Sonra kamp 7m icindeki yabanci (agac/prop disi) objeleri raporla."""
import sys, time, json, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

log = []
before = ap.child_count("CampForest")
ok = ap.rc("delete_object", {"name": "CampForest"}, 20)
time.sleep(1); ap.fresh()
after = ap.child_count("CampForest")
log.append(f"CampForest {before} -> {after} (sil={ok})")

# kamp 7m icindeki yabanci objeler (magenta/shard kaynagi olabilir)
r = ap.rc("list_scene_objects", {"max_count": 5000}, 40) or {}
objs = r.get("objects") or []
cx, cz = -526.0, -98.0
keep = ("Campfire", "FireStone", "LogSeat", "Firewood", "CampStorage", "CampLantern",
        "CampFern", "Hearth", "Lantern", "CampHub", "WoodHouse", "RumorBoard",
        "CraftStation", "PlayerSpawn", "CampSite", "CampDressing", "CampWarmth", "Camp")
near = []
for o in objs:
    p = o.get("position") or {}; nm = str(o.get("name", ""))
    d = math.hypot(p.get("x", 0) - cx, p.get("z", 0) - cz)
    if d < 7 and not any(k in nm for k in keep):
        near.append([nm[:26], round(d, 1), round(p.get("y", 0), 0)])
log.append("kamp_7m_yabanci=" + json.dumps(near[:25], ensure_ascii=False))
log.append("WorldForestGLB=" + str(ap.child_count("WorldForestGLB")))
log.append("SAVE=" + str(ap.save()))
log.append("CLEAR_DONE")
Path("studio/autopilot/_clear.txt").write_text("\n".join(log), encoding="utf-8")
print("CLEAR_DONE")
