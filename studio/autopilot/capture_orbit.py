"""ORBIT/KAPSAM CAPTURE: bir hedef nokta cevresinde COK SAYIDA acidan otomatik
snapshot ceker (autopilot'un 'surekli snapshot' motoru). Sonra shot_triage.py ile
elenir. 3000'e kadar kare hedefleniyor ama capture bridge-timeout'una takilmasin
diye guvenli partiler halinde + her N karede tekrar baglanir.

Kullanim:
  python capture_orbit.py <merkez_obj_veya_xz> [yaricap_listesi] [yaw_adim] [pitch_listesi]
  ornek: python capture_orbit.py Campfire
         python capture_orbit.py -482,-311 60,120,200 30 5,20,40
"""
import sys, time, json, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *

def parse_center(s):
    o = pos_of(s)
    if o: return o[0], o[1], o[2]
    try:
        x, z = s.split(","); return float(x), 80.0, float(z)
    except Exception:
        return -526.0, 142.0, -98.0

connect(); guard_scene()
arg = sys.argv[1] if len(sys.argv) > 1 else "Campfire"
cx, cy, cz = parse_center(arg)
sizes  = [float(s) for s in (sys.argv[2].split(",") if len(sys.argv) > 2 else "55,110,200".split(","))]
yawstep= int(sys.argv[3]) if len(sys.argv) > 3 else 30
pitches= [float(s) for s in (sys.argv[4].split(",") if len(sys.argv) > 4 else "4,16,34".split(","))]

from ap import _studio_shot
n = 0
yaws = list(range(0, 360, yawstep))
total = len(sizes)*len(pitches)*len(yaws)
print(f"ORBIT hedef=({cx:.0f},{cy:.0f},{cz:.0f}) toplam_kare={total}")
for si, size in enumerate(sizes):
    for pit in pitches:
        for yaw in yaws:
            try:
                rc("set_scene_view", {"pivot_x":cx,"pivot_y":cy+size*0.12,"pivot_z":cz,
                    "size":size,"pitch":pit,"yaw":yaw}, 25)
                time.sleep(0.4)
                _studio_shot(name=f"orbit_s{int(size)}_p{int(pit)}_y{yaw}")
                n += 1
            except Exception:
                fresh(); time.sleep(1)
            if n % 20 == 0:
                fresh()  # her 20 karede baglantiyi tazele (timeout onleme)
Path("studio/autopilot/_orbit.txt").write_text(json.dumps({"cekilen":n,"hedef":total}), encoding="utf-8")
print(f"ORBIT_DONE cekilen={n}")
