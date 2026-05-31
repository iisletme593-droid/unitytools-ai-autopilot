import sys, time, json, math; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
save()
cf=pos_of("Campfire") or (-526,141,-98)
kp=pos_of("GothicCastle") or (-503,106,-178)
# kamptan kaleye dogru bakan establishing
yaw=math.degrees(math.atan2(kp[0]-cf[0], kp[2]-cf[2]))
rc("set_scene_view", {"pivot_x":cf[0],"pivot_y":cf[1]+9,"pivot_z":cf[2],"size":75,"pitch":5,"yaw":yaw}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="FINAL")
Path("studio/autopilot/_final.txt").write_text((r or {}).get("source",""), encoding="utf-8")
