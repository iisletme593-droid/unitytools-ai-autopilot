import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
rc("setup_hdrp_volume", {"fog":True,"fog_distance":600.0,"exposure_mode":"Fixed","fixed_exposure":14.5}, 20)
save()
Path("studio/autopilot/_setev.txt").write_text("EV=14.5 uygulandi + kaydedildi", encoding="utf-8")
