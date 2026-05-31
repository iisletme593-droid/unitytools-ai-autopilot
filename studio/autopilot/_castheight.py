import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
d = rc("get_object_details", {"name":"GothicCastle"}, 15) or {}
p = d.get("position") or {}
cx=float(p.get("x",-482)); cy=float(p.get("y",95)); cz=float(p.get("z",-311))
ground = surf(cx, cz, cy)
out=[f"kale_pivot_y={cy:.1f}", f"arazi_yuzey_y={ground:.1f}", f"fark={cy-ground:.1f}"]
# pivot tabanda mi merkezde mi? bounds 156 -> yari ~78. pivot tabandaysa cy~ground olmali
Path("studio/autopilot/_ch2.txt").write_text("\n".join(out), encoding="utf-8")
