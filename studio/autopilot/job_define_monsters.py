"""CANAVAR/BOLGE TANIMI — mevcut MonsterSpawn marker'larini arketip/tier ile
yapilandir (olgun sistem: EnemySpawnPoint bilesenleri). set_component reflection.
add_component ile EnemySpawnPoint yoksa ekle. Play KAPALI.
Tasarim: BOLGE-CANAVAR-TASARIM.md."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

# marker -> (archetype_index, tier, maxConcurrent, respawn)
PLAN = {
    "MonsterSpawn_00": (0, 1, 3, 25),  # Wanderer
    "MonsterSpawn_01": (5, 1, 5, 20),  # Swarm
    "MonsterSpawn_02": (0, 1, 3, 25),  # Wanderer
    "MonsterSpawn_03": (1, 2, 2, 30),  # Stalker
    "MonsterSpawn_04": (2, 2, 2, 35),  # Brute
    "MonsterSpawn_05": (5, 2, 5, 22),  # Swarm
    "MonsterSpawn_06": (3, 2, 2, 30),  # Archer
    "MonsterSpawn_07": (1, 2, 2, 30),  # Stalker
    "MonsterSpawn_08": (2, 3, 2, 35),  # Brute
    "MonsterSpawn_09": (4, 3, 1, 40),  # Caster
    "BossSpawn":       (6, 4, 1, 0),   # Elite
}

ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

log = []
ok = 0
for nm, (arch, tier, mx, resp) in PLAN.items():
    d = ap.rc("get_object_details", {"name": nm}, 12) or {}
    if not d.get("name"):
        log.append(f"{nm}: YOK (atlandi)"); continue
    # EnemySpawnPoint bileseni ekle (varsa no-op olabilir)
    ap.rc("add_component", {"name": nm, "component": "EnemySpawnPoint"}, 12)
    # alanlari ayarla
    r = ap.rc("set_component", {"object": nm, "component": "EnemySpawnPoint",
              "values": {"archetype": arch, "tier": tier, "maxConcurrent": mx,
                         "respawnSeconds": resp, "spawnChance": 1.0, "radius": 6.0}}, 14)
    good = isinstance(r, dict) and (r.get("ok") or r.get("set") or "EnemySpawnPoint" in str(r))
    if good: ok += 1
    log.append(f"{nm}: arch={arch} tier={tier} -> {str(r)[:60]}")

log.append(f"YAPILANDIRILDI={ok}/{len(PLAN)}")
log.append("SAVE=" + str(ap.save()))
log.append("DEFINE_DONE")
Path("studio/autopilot/_monsters.txt").write_text("\n".join(log), encoding="utf-8")
print("DEFINE_DONE ok=%d" % ok)
