import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
fp = pos_of("Campfire") or (-526,142,-98); fx,fy,fz=fp
import math
p = shot("ap_camp", fx, fy+5, fz, 22, 6, 200)
print("SHOT", p)
