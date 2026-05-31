"""Oto-QA: bir hedef etrafinda N kare cek -> her birini SAYISAL analiz et
(parlaklik, yesil%, siyah-blok%, pembe/bozuk%) -> hepsini tek KONTAK-SHEET
(grid) resme birlestir. Boylece Claude 1 resim okuyup 16 kareyi birden gorur,
+ verdict.txt'te hangi kareler supheli yazar.

Kullanim: python autoqa.py <hedef_obj> <N> [orbit_size]
Cikti: studio/autopilot/qa_sheet.png (grid) + studio/autopilot/qa_verdict.txt
"""
import sys, time, json, math
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
from PIL import Image
import numpy as np

target = sys.argv[1] if len(sys.argv)>1 else "Campfire"
N      = int(sys.argv[2]) if len(sys.argv)>2 else 12
SIZE   = float(sys.argv[3]) if len(sys.argv)>3 else 80.0

connect(); guard_scene()
tp = pos_of(target) or (-526,142,-98)
cx,cy,cz = tp

def analyze(path):
    a = np.array(Image.open(path).convert("RGB"))
    r,g,b = a[:,:,0].astype(int), a[:,:,1].astype(int), a[:,:,2].astype(int)
    bright = float(a.mean())
    green  = float(((g>r)&(g>b)&(g>45)).mean())
    black  = float((a.max(axis=2)<35).mean())          # siyah blok / bos
    pink   = float(((r>150)&(b>120)&(g<r-40)).mean())  # bozuk HDRP malzeme
    wash   = float((a.min(axis=2)>225).mean())         # asiri pozlama/beyaz
    flags=[]
    if bright<25: flags.append("KARANLIK")
    if wash>0.25: flags.append("YIKANMIS")
    if black>0.35: flags.append("SIYAH-BLOK")
    if pink>0.05: flags.append("PEMBE-BOZUK")
    return dict(bright=round(bright), green=round(green,2), black=round(black,2),
                pink=round(pink,3), wash=round(wash,2), flags=flags)

frames=[]; verdict=[]
for i in range(N):
    yaw = (i/N)*360.0
    rc("set_scene_view", {"pivot_x":cx,"pivot_y":cy+10,"pivot_z":cz,
                          "size":SIZE,"pitch":8,"yaw":yaw}, 30)
    time.sleep(0.8)
    r = _studio_shot(name=f"qa_{i:02d}")
    src = (r or {}).get("source","")
    if not src or not Path(src).exists():
        verdict.append(f"#{i:02d} yaw{int(yaw)}: KARE ALINAMADI"); continue
    st = analyze(src)
    frames.append((src, i, int(yaw), st))
    verdict.append(f"#{i:02d} yaw{int(yaw):3d}: parlak{st['bright']} yesil{st['green']} "
                   f"siyah{st['black']} pembe{st['pink']} {' '.join(st['flags']) or 'OK'}")

# KONTAK-SHEET: grid montaj
if frames:
    cols = 4; rows = math.ceil(len(frames)/cols)
    tw,th = 320,180
    sheet = Image.new("RGB",(cols*tw, rows*th),(20,20,20))
    for idx,(src,i,yaw,st) in enumerate(frames):
        im = Image.open(src).convert("RGB").resize((tw,th))
        sheet.paste(im, ((idx%cols)*tw, (idx//cols)*th))
    sheet.save("studio/autopilot/qa_sheet.png")

Path("studio/autopilot/qa_verdict.txt").write_text(
    f"hedef={target} N={len(frames)}/{N}\n"+"\n".join(verdict), encoding="utf-8")
print("AUTOQA_DONE", len(frames))
