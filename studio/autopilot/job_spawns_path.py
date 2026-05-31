"""Rebuild MonsterSpawns (10 slots around camp) + PathRoute (7 nodes camp->castle)
+ ensure PlayerSpawn at the campfire. ap-based, correct scene, verified."""
import sys, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from ap import *

connect()
if not guard_scene(): print("GUARD_FAIL"); sys.exit(1)

cf = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
ks = pos_of("GothicCastle", -482, 96, -311)
cx, cy, cz = cf
print(f"CAMP {cx:.0f},{cy:.0f},{cz:.0f}  CASTLE {ks[0]:.0f},{ks[2]:.0f}")

# PlayerSpawn beside the fire
fy = surf(cx, cz, cy)
empty("PlayerSpawn", cx-3, fy+1.0, cz-3)
rc("set_tag", {"name":"PlayerSpawn","tag":"Respawn"}, 10)

# Monster slots
group("MonsterSpawns", cx, cy, cz)
ms = 0
for i in range(10):
    a=(i/10)*math.tau; rad=38+(i%3)*20
    mx=cx+math.cos(a)*rad; mz=cz+math.sin(a)*rad; my=surf(mx,mz,cy)
    if my<5: continue
    empty(f"MonsterSpawn_{i:02d}", mx, my+0.5, mz, parent="MonsterSpawns"); ms+=1
print(f"MONSTER {ms}")

# Path nodes camp->castle
group("PathRoute", cx, cy, cz)
wp=0
for i in range(7):
    t=i/6.0; px=cx+(ks[0]-cx)*t; pz=cz+(ks[2]-cz)*t; py=surf(px,pz,cy)
    if py<5: continue
    empty(f"PathNode_{i:02d}", px, py+0.2, pz, parent="PathRoute"); wp+=1
print(f"PATH {wp}")
print("SAVE", save())
print("JOB_DONE spawns path")
