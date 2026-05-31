import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
import math
cf = pos_of("Campfire") or (-526,142,-98)
p = shot("ap_progress", cf[0]+20, cf[1]+18, cf[2]+20, 70, 14, 210)
print("SHOT", p)
