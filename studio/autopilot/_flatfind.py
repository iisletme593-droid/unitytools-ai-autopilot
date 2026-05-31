import sys, json, math; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# arazide DUZ + makul yukseklikte bir nokta ara (probe ile 5x5 grid orta bolge)
best=None
for gx in range(-200, 201, 80):
    for gz in range(-200, 201, 80):
        ys=[surf(gx+dx, gz+dz, 60) for dx in (-15,0,15) for dz in (-15,0,15)]
        flat=max(ys)-min(ys); avg=sum(ys)/len(ys)
        if 30 < avg < 120 and (best is None or flat<best[0]):
            best=(flat, gx, round(avg), gz)
Path("studio/autopilot/_flat.txt").write_text(json.dumps({"en_duz":best}), encoding="utf-8")
