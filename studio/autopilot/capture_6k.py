"""6000+ KARE OTONOM CAPTURE motoru — autopilot 'sürekli snapshot' beni besler.
Tüm anahtar POI'ler (kamp, kale, göl, bölgeler, knight) etrafında İNCE açısal
çözünürlükte (milisaniye-yoğun his) orbit çeker. Bridge-timeout'a karşı her 20
karede reconnect + parti parti. Sonra shot_triage 6000'i ~30 çeşitli kareye eler.

Güncel dünya (relocate sonrası):
  Kamp (-80,340) · Kale (285,345) · Göl ortası (60,340) · Knight (-84,344)
  t1 region (-5,340) · t2/t3 SW (-150,300)

Kullanım: python capture_6k.py [hedef_kare=6000]
"""
import sys, time, math, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 6000

ap.connect(); time.sleep(2)
es = ap.rc('get_editor_state', {}, 20) or {}
if es.get('is_playing'): ap.rc('play_mode', {'play': False}, 40); time.sleep(3); ap.fresh()
ap.guard_scene()

# (ad, cx, cy, cz, size_listesi) — POI'ler
POIS = [
    ("camp",    -80, 11, 340, [6, 9, 14, 22, 36]),
    ("knight",  -84, 11, 344, [4, 6, 9]),
    ("castle",  285, 75, 345, [40, 62, 90, 140]),
    ("lake",     60, 30, 340, [120, 180, 260]),
    ("t1",       -5, 12, 340, [20, 40, 70]),
    ("danger", -150, 50, 300, [60, 110, 180]),
    ("aerial",  100, 70, 342, [200, 280, 360]),
]
# ince açısal çözünürlük (milisaniye-yoğun): yaw her 12°, pitch çok kademe
YAWS = list(range(0, 360, 12))      # 30 yaw
PITCHES = [3, 8, 14, 22, 32, 45]     # 6 pitch

n = 0
batch = 0
log_path = Path("studio/autopilot/_cap6k.txt")
t0 = time.time()
done = False
for (name, cx, cy, cz, sizes) in POIS:
    if done: break
    for size in sizes:
        if done: break
        for pit in PITCHES:
            if done: break
            for yaw in YAWS:
                try:
                    ap.rc('set_scene_view', {'pivot_x': cx, 'pivot_y': cy + size * 0.10,
                          'pivot_z': cz, 'size': size, 'pitch': pit, 'yaw': yaw}, 20)
                    ap._studio_shot(name=f"k6_{name}_s{int(size)}_p{int(pit)}_y{yaw}")
                    n += 1
                except Exception:
                    ap.fresh(); time.sleep(0.6)
                if n % 20 == 0:
                    ap.fresh()  # timeout önleme
                if n % 100 == 0:
                    log_path.write_text(json.dumps({"cekilen": n, "hedef": TARGET,
                        "poi": name, "gecen_s": round(time.time()-t0)}), encoding='utf-8')
                if n >= TARGET:
                    done = True
log_path.write_text(json.dumps({"cekilen": n, "hedef": TARGET, "gecen_s": round(time.time()-t0),
    "BITTI": True}), encoding='utf-8')
print(f"CAP6K_DONE cekilen={n}")
