import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
res={}
cf = pos_of("Campfire") or (-526,142,-98)
from ap import _studio_shot
for ev in [13.5, 14.5]:
    rc("setup_hdrp_volume", {"fog":True,"fog_distance":600.0,"exposure_mode":"Fixed","fixed_exposure":ev}, 20)
    time.sleep(0.5); fresh()
    rc("set_scene_view", {"pivot_x":cf[0],"pivot_y":cf[1]+8,"pivot_z":cf[2],"size":60,"pitch":4,"yaw":200}, 30)
    time.sleep(1.4)
    r=_studio_shot(name=f"ev{int(ev*10)}")
    res[f"ev{ev}"]=(r or {}).get("source")
Path("studio/autopilot/_evtest.txt").write_text(json.dumps(res), encoding="utf-8")
