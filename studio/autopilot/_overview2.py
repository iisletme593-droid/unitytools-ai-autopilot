import sys, math, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# kamp + kale ayni karede (kompozisyon kontrol)
cf = pos_of("Campfire") or (-526,142,-98)
kp = pos_of("GothicCastle") or (-482,95,-311)
out=[f"kamp={cf}", f"kale={kp}", f"mesafe={math.hypot(cf[0]-kp[0],cf[2]-kp[2]):.0f}m"]
mx,mz=(cf[0]+kp[0])/2,(cf[2]+kp[2])/2
yaw=math.degrees(math.atan2(kp[0]-cf[0], kp[2]-cf[2]))
rc("set_scene_view",{"pivot_x":mx,"pivot_y":max(cf[1],kp[1])+50,"pivot_z":mz,"size":230,"pitch":16,"yaw":yaw},30)
time.sleep(1.3)
from ap import _studio_shot
_studio_shot(name="full_overview")
out.append("shot=full_overview")
Path("studio/autopilot/_ov.txt").write_text("\n".join(out), encoding="utf-8")
