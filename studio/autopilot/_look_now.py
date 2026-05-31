import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# kamp ile kaleyi ayni karede goren genis establishing (kullanicinin gordugu manzara)
cf = pos_of("Campfire") or (-526,142,-98)
import math
# kamptan kaleye dogru bak, hafif yukaridan
rc("set_scene_view", {"pivot_x":cf[0],"pivot_y":cf[1]+8,"pivot_z":cf[2],"size":60,"pitch":4,"yaw":200}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="LOOK")
# capture'in DONDURDUGU gercek yollari yaz
Path("studio/autopilot/_look_now.txt").write_text(json.dumps(r), encoding="utf-8")
