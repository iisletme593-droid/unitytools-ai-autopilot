"""CANAVARLARI YERLESTIR — her spawn marker'ina arketip-uygun enemy mesh +
tuned EnemyAIController + CombatComponent. EnemyRespawnDirector Start'ta otomatik
kaydeder. Hepsi 'Monsters' grubunda (geri alinabilir). Play KAPALI.

Arketipler (BOLGE-CANAVAR-TASARIM.md):
  mesh: SK_Enemy0.fbx (FBX) / SK_Enemy1.fbx (FBX) / enemy_brute_barbarian.glb (GLB)
  her arketip: hp, speed, dmg, chase, scale, count farkli -> gercek bestiary
"""
import sys, time, json, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

E0 = "Assets/Art/Characters/Imported/Enemy/SK_Enemy0.fbx"   # FBX (Z-up)
E1 = "Assets/Art/Characters/Imported/Enemy/SK_Enemy1.fbx"   # FBX (Z-up)
BRUTE = "Assets/Art/Characters/Enemy/hf3d_enemy_brute_barbarian.glb"  # GLB (Y-up)

# arketip -> (mesh, glb?, hp, speed, dmg, chase, scale, count, isim)
ARCH = {
  0: (E0,    False,  80, 3.2, 10, 13, 1.0, 1, "Wanderer"),
  1: (E1,    False,  70, 5.2, 12, 18, 1.0, 1, "Stalker"),
  2: (BRUTE, True,  220, 2.4, 26, 11, 1.5, 1, "Brute"),
  3: (E1,    False,  60, 3.0, 14, 22, 1.0, 1, "Archer"),
  4: (E0,    False,  90, 2.8, 18, 16, 1.1, 1, "Caster"),
  5: (E0,    False,  35, 4.2,  7, 14, 0.7, 3, "Swarm"),
  6: (BRUTE, True,  600, 2.8, 40, 16, 2.2, 1, "Elite"),
}
# marker -> archetype
PLAN = {
  "MonsterSpawn_00": 0, "MonsterSpawn_01": 5, "MonsterSpawn_02": 0,
  "MonsterSpawn_03": 1, "MonsterSpawn_04": 2, "MonsterSpawn_05": 5,
  "MonsterSpawn_06": 3, "MonsterSpawn_07": 1, "MonsterSpawn_08": 2,
  "MonsterSpawn_09": 4, "BossSpawn": 6,
}

log = []
def L(m): log.append(m); Path("studio/autopilot/_placemon.txt").write_text("\n".join(log), encoding="utf-8")

ap.connect(); time.sleep(2)
es = ap.rc("get_editor_state", {}, 20) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

# spawn konumlarini guvenilir al (find)
spawns = {}
r = ap.rc("find_scene_objects", {"name_contains": "Spawn", "max_count": 40}, 25) or {}
for o in (r.get("objects") or []):
    nm = o.get("name", "")
    if nm in PLAN:
        p = o.get("position") or {}
        spawns[nm] = (p.get("x", 0), p.get("z", 0))
L(f"spawn_bulundu={len(spawns)}/{len(PLAN)}")

for _ in range(2): ap.rc("delete_object", {"name": "Monsters"}, 10)
ap.rc("create_empty", {"name": "Monsters", "position": {"x": -526, "y": 142, "z": -98}}, 12)

total = 0
for marker, arch in PLAN.items():
    if marker not in spawns:
        L(f"{marker}: konum yok, atla"); continue
    sx, sz = spawns[marker]
    mesh, is_glb, hp, spd, dmg, chase, scale, count, name = ARCH[arch]
    for i in range(count):
        # swarm icin kucuk dagilim
        ox = math.cos(i * 2.1) * (2.5 if count > 1 else 0)
        oz = math.sin(i * 2.1) * (2.5 if count > 1 else 0)
        nm = f"Mob_{name}_{marker[-2:]}_{i}"
        r = ap.place_pinned(mesh, sx + ox, sz + oz, scale, nm, parent="Monsters",
                            glb=is_glb, rot_y=(i*70) % 360, y_offset=0.0,
                            min_surface_y=5.0, max_slope_deg=89.0)
        if not r:
            L(f"  {nm}: place FAIL"); continue
        # AI + combat
        ap.rc("configure_behaviour_component", {"object_name": nm,
              "behaviour_name": "EnemyAIController",
              "fields": {"moveSpeed": spd, "attackDamage": dmg, "chaseRange": chase,
                         "attackRange": 2.2, "patrolRadius": 6.0}}, 14)
        ap.rc("configure_behaviour_component", {"object_name": nm,
              "behaviour_name": "CombatComponent",
              "fields": {"maxHealth": hp, "factionId": 2}}, 14)  # 2 = hostile
        total += 1
    L(f"{marker}: {name} x{count} ({arch})")
    ap.fresh()

L(f"TOPLAM_CANAVAR={total}")
L("Monsters_cc=" + str(ap.child_count("Monsters")))
L("forest=" + str(ap.child_count("WorldForestGLB")))
L("SAVE=" + str(ap.save()))
L("PLACEMON_DONE")
print("PLACEMON_DONE total=%d" % total)
