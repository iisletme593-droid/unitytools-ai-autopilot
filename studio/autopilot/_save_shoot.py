import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
out.append("forest="+str(child_count("WorldForestGLB")))
out.append("SAVE="+str(save()))
# dogru isik
rc("setup_hdrp_volume", {"fog":True,"fog_distance":700.0,"exposure_mode":"Fixed","fixed_exposure":13.8}, 20)
# kamptan kare
cf=pos_of("Campfire") or (-526,142,-98)
rc("set_scene_view", {"pivot_x":cf[0],"pivot_y":cf[1]+12,"pivot_z":cf[2],"size":90,"pitch":8,"yaw":200}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="FOREST_BACK")
out.append("shot="+(r or {}).get("source",""))
Path("studio/autopilot/_ss.txt").write_text("\n".join(out), encoding="utf-8")
