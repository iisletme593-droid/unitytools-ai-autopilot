import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# yuksekten kus bakisi: tum haritayi gor, agaclarin nerede oldugunu anla
# harita merkezi 0,0; 1200m harita. Yuksek + genis.
rc("setup_hdrp_volume", {"fog":True,"fog_distance":900.0,"exposure_mode":"Fixed","fixed_exposure":13.5}, 20)
rc("set_scene_view", {"pivot_x":-300,"pivot_y":260,"pivot_z":-200,"size":600,"pitch":42,"yaw":40}, 30)
time.sleep(1.6)
from ap import _studio_shot
r=_studio_shot(name="SCOUT")
Path("studio/autopilot/_scout.txt").write_text((r or {}).get("source",""), encoding="utf-8")
