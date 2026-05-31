"""Spawn sistemi tasarimi: MonsterSpawn markerlari runtime-spawner mi yoksa bos
Transform mi? TI_EnemyRespawnDirector bilesenlerini + bir spawn markerini incele.
Buna gore: bos ise enemy mesh yerlestir, spawner ise runtime'a birak."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

out = {}
def comps(nm):
    d = ap.rc("get_object_details", {"name": nm}, 16) or {}
    cs = d.get("components") or []
    return [c.get("type") if isinstance(c, dict) else str(c) for c in cs]

for nm in ("TI_EnemyRespawnDirector", "MonsterSpawns", "MonsterSpawn_00",
           "MonsterSpawn_01", "BossSpawn", "EncounterMarkers"):
    out[nm] = comps(nm)

# MonsterSpawns alt-cocuklarinin sayisi + isim ornegi
d = ap.rc("get_object_details", {"name": "MonsterSpawns"}, 16) or {}
out["_MonsterSpawns_cc"] = d.get("child_count")

# enemy mesh varligi (diskte dogrulandi)
out["_enemy_meshes"] = ["Art/Characters/Imported/Enemy/SK_Enemy0.fbx",
                        "Art/Characters/Imported/Enemy/SK_Enemy1.fbx",
                        "Art/Characters/Enemy/hf3d_enemy_brute_barbarian.glb"]
Path("studio/autopilot/_spawndiag.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
print("SPAWNDIAG_DONE")
