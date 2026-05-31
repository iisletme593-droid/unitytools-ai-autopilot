import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
names=["WorldForestGLB","WoodHouse","GothicCastle","LightBeam","CampSite","CampDressing",
       "CampWarmth","RoadDressing","FernUndergrowth","RockScatter","RumorBoard",
       "BossArena","BossSpawn","MonsterSpawns","PathRoute","PlayerSpawn"]
out=[]
for nm in names:
    d=rc("get_object_details",{"name":nm},12) or {}
    out.append(f"{nm}={d.get('child_count') if d.get('name') else 'MISSING'}")
Path("studio/autopilot/_inv.txt").write_text(" | ".join(out), encoding="utf-8")
print("WROTE_INV")
