import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
cf = pos_of("Campfire") or (-526,142,-98)
shot("pbr_ground", cf[0]+8, cf[1]+5, cf[2]+8, 20, 22, 40)
shot("pbr_wide", cf[0]+40, cf[1]+30, cf[2]+40, 130, 14, 40)
