import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_craft2.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
# CraftBench varsa onun yanina, yoksa kampin yanina koy
cb = pos_of("CraftBench")
if cb is None:
    cf = pos_of("Campfire") or pos_of("WoodHouse", -533, 138, -105)
    cb = (cf[0] + 9, cf[1], cf[2] + 12)
x, y, z = cb
sy = surf(x, z, y)
empty("CraftStation", x, sy + 0.5, z)
ok = pos_of("CraftStation") is not None
saved = save()
Path("studio/autopilot/_craft2.txt").write_text(
    f"CraftStation={('OK' if ok else 'YOK')} at {x:.0f},{sy:.0f},{z:.0f} saved={saved}",
    encoding="utf-8")
