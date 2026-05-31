import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene(): print("GUARD_FAIL"); sys.exit(1)
cb = pos_of("CraftBench")
if cb is None:
    cf = pos_of("Campfire") or pos_of("WoodHouse", -533,138,-105)
    cb = (cf[0]+9, cf[1], cf[2]+12)
x, y, z = cb
sy = surf(x, z, y)
empty("CraftStation", x, sy+0.5, z)
Path("studio/autopilot/_craft.txt").write_text(
    f"CRAFTSTATION {x:.0f},{sy:.0f},{z:.0f} exists={child_count('CraftStation') is not None} SAVE={save()}",
    encoding="utf-8")
print("OK")
