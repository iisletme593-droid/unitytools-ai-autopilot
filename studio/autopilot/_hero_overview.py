import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# kamp/ev ile kaleyi ayni karede goren genis establishing
cf = pos_of("Campfire") or (-526,142,-98)
kp = pos_of("GothicCastle") or (-482,95,-311)
import math
mx,mz=(cf[0]+kp[0])/2,(cf[2]+kp[2])/2
yaw=math.degrees(math.atan2(kp[0]-cf[0], kp[2]-cf[2]))
shot("overview_a", cf[0], cf[1]+18, cf[2], 120, 6, yaw)
shot("overview_b", mx, max(cf[1],kp[1])+45, mz, 200, 16, yaw)
