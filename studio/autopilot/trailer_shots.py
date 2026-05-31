"""TRAILER ÇEKİM — ThornIvy / Briar Hollow tanıtım videosu için sinematik kareler.
8 sahne, her biri lore'dan bir Türkçe başlık + Unity kamera açısı. Yüksek-aci
(canopy üstü) + en iyi kamp/kale açıları kullanılır (playbook'tan). EV9 moody.
Her kare 1920x1080 yakalanır; ffmpeg sonra birleştirir.
"""
import sys, time, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
from PIL import Image

ap.connect(); time.sleep(2)
es = ap.rc('get_editor_state', {}, 20) or {}
if es.get('is_playing'): ap.rc('play_mode', {'play': False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

OUT = Path("studio/autopilot/trailer"); OUT.mkdir(parents=True, exist_ok=True)

# (id, pivot_x, y, z, size, pitch, yaw) — sinematik açılar
SHOTS = [
    ("01_valley",   100,  75, 342, 240, 18,  90),   # genis vadi + gol + kale
    ("02_camp",     -80, 10.5,340,   9,  5,  45),   # kamp ates+kabin (sicak)
    ("03_cabin",    -90,  12, 350,   8,  8, 135),   # ahsap kabin yakin
    ("04_castle",   285,  85, 345,  62, 12,  25),   # gotik kale + god-ray
    ("05_lake",     120,  50, 343, 175,  9,  90),   # gol uzerinden kaleye
    ("06_rocks",   -100,  16, 320,  22, 18,  30),   # kaya + flora (dunya dokusu)
    ("07_danger",  -180,  55, 300,  80, 22, 120),   # tehlike bolgesi (olu agac)
    ("08_aerial",  150,  90, 343, 300, 30,  90),    # epik aerial finale
]
log = []
for sid, px, py, pz, size, pitch, yaw in SHOTS:
    ap.rc('set_scene_view', {'pivot_x': px, 'pivot_y': py, 'pivot_z': pz,
                              'size': size, 'pitch': pitch, 'yaw': yaw}, 30)
    time.sleep(1.6)
    r = ap._studio_shot(name=f"tr_{sid}") or {}
    src = str(Path(os.getcwd()) / r.get('path', ''))
    if os.path.exists(src):
        im = Image.open(src).convert('RGB')
        # 1920x1080'e zorla (cinematic)
        im = im.resize((1920, 1080))
        im.save(OUT / f"{sid}.png")
        log.append(f"{sid}: OK")
    else:
        log.append(f"{sid}: MISS {src}")
Path("studio/autopilot/_trailer.txt").write_text("\n".join(log), encoding='utf-8')
print("TRAILER_SHOTS_DONE")
