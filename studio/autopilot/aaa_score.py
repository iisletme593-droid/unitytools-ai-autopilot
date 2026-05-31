"""BONUS B: AAA SINEMATIK KALITE SKORU — bir kareye sanat-yonetmeni gozuyle
0-100 puan verir. Triyaj 'bozuk'lari eler; bu modul 'guzel'leri SIRALAR ->
en sinematik beauty-shot acisini otomatik bulur.

Kriterler (her biri 0-1, agirlikli toplam *100):
  comp_thirds : ilgi/detay ucte-bir cizgilerinde mi (rule of thirds)
  horizon     : ufuk cok ortada/cok kenarda degil mi (alt-ucte-bir ideal)
  depth       : on/orta/arka katman parlaklik farki (derinlik hissi)
  color_harm  : renk paleti uyumu (asiri doygun/cakisik degil, sicak-soguk denge)
  contrast    : ton araligi saglikli mi (ne yikanik ne ezik)
  exposure    : ortalama parlaklik tatli noktada mi (~90-150)
  focus       : detay/keskinlik yeterli mi (bos/bulanik degil)
  framing     : kenar bosluklari dengeli, asiri-bos-gokyuzu cezasi

Kullanim: python aaa_score.py [png_klasoru] [top=8]
Cikti: studio/autopilot/_aaa.json + en iyi kareler studio/autopilot/beauty/
"""
import sys, os, json, glob
from pathlib import Path
try:
    from PIL import Image
    import numpy as np
except Exception as e:
    print("PIL/numpy gerekli:", e); sys.exit(1)

SRC = sys.argv[1] if len(sys.argv) > 1 else \
    "C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject/AutopilotData/screenshots"
TOP = int(sys.argv[2]) if len(sys.argv) > 2 else 8
OUT = "studio/autopilot/beauty"

W = {  # agirliklar (toplam 1.0)
    "comp_thirds": 0.16, "horizon": 0.12, "depth": 0.18, "color_harm": 0.14,
    "contrast": 0.12, "exposure": 0.12, "focus": 0.10, "framing": 0.06,
}

def score_frame(path):
    im = Image.open(path).convert("RGB"); im.thumbnail((320, 320))
    a = np.asarray(im).astype(np.float32)
    h, w, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299*r + 0.587*g + 0.114*b
    mean = float(lum.mean())

    # exposure: 90-150 tatli nokta, disina dogru ceza
    expo = max(0.0, 1.0 - abs(mean - 120) / 110)

    # contrast: saglikli std (~45-75 ideal), yikanik/ezik cezali
    std = float(lum.std()); contrast = max(0.0, 1.0 - abs(std - 60) / 75)
    blown = float((lum > 250).mean()); crushed = float((lum < 10).mean())
    contrast *= (1 - min(1, blown*4)) * (1 - min(1, crushed*2))

    # focus: Laplacian varyansi normalize
    L = lum
    lap = np.abs(4*L[1:-1,1:-1]-L[:-2,1:-1]-L[2:,1:-1]-L[1:-1,:-2]-L[1:-1,2:])
    focus = min(1.0, lap.var() / 2500.0)

    # depth: alt(on)/orta/ust(arka) parlaklik farkliligi -> katmanli sahne
    top = lum[:h//3].mean(); mid = lum[h//3:2*h//3].mean(); bot = lum[2*h//3:].mean()
    depth = min(1.0, (np.std([top, mid, bot]) / 45.0))

    # horizon: en buyuk yatay parlaklik-gradyan satiri (ufuk) nerede
    rowmean = lum.mean(1)
    grad = np.abs(np.diff(rowmean))
    hy = (int(np.argmax(grad)) / h) if grad.size else 0.5
    # ideal ufuk ust-ucte-bir (0.33) civari; 0.33'e yakinlik
    horizon = max(0.0, 1.0 - abs(hy - 0.36) / 0.5)

    # comp_thirds: detay (lokal varyans) ucte-bir kesisimlerinde mi
    gy = np.abs(np.gradient(lum)[0]) + np.abs(np.gradient(lum)[1])
    def patch(cx, cy):
        y0,y1 = int(cy*h)-h//12, int(cy*h)+h//12
        x0,x1 = int(cx*w)-w//12, int(cx*w)+w//12
        return gy[max(0,y0):y1, max(0,x0):x1].mean()
    inter = np.mean([patch(x,y) for x in (1/3,2/3) for y in (1/3,2/3)])
    comp_thirds = min(1.0, inter / max(1e-3, gy.mean()*1.4))

    # color_harm: doygunluk makul (cok soluk/cok neon degil) + sicak-soguk denge
    mx = a.max(2); mn = a.min(2)
    sat = np.where(mx>0, (mx-mn)/np.maximum(mx,1), 0).mean()
    sat_ok = max(0.0, 1.0 - abs(sat - 0.32)/0.5)
    warm = float((r > b).mean()); balance = 1.0 - abs(warm - 0.55)  # hafif sicak ideal
    color_harm = 0.6*sat_ok + 0.4*max(0.0, balance)

    # framing: asiri-bos gokyuzu (ust yarisi cok duz+parlak) cezasi
    sky_flat = 1.0 - min(1.0, lum[:h//2].std()/40.0)
    framing = 1.0 - 0.6*sky_flat*( (lum[:h//2].mean()>150) )

    parts = {"comp_thirds":comp_thirds,"horizon":horizon,"depth":depth,
             "color_harm":color_harm,"contrast":contrast,"exposure":expo,
             "focus":focus,"framing":max(0.0,framing)}
    total = sum(W[k]*parts[k] for k in W) * 100
    parts = {k: round(v,2) for k,v in parts.items()}
    return round(total,1), parts

def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.png")), key=os.path.getmtime)
    if not files:
        print("KARE YOK:", SRC); return
    rows = []
    for f in files:
        try:
            sc, parts = score_frame(f)
            rows.append({"file":f,"aaa":sc,**parts})
        except Exception:
            pass
    rows.sort(key=lambda x: -x["aaa"])
    Path(OUT).mkdir(parents=True, exist_ok=True)
    for old in glob.glob(os.path.join(OUT,"*.png")): os.remove(old)
    best=[]
    for i,r in enumerate(rows[:TOP]):
        dst=os.path.join(OUT,f"BEAUTY_{i:02d}_aaa{int(r['aaa'])}.png")
        Image.open(r["file"]).convert("RGB").resize((480,270)).save(dst)
        best.append({"rank":i,"aaa":r["aaa"],"beauty":dst,"src":os.path.basename(r["file"]),
                     **{k:r[k] for k in W}})
    rep={"taranan":len(rows),
         "ort_aaa":round(sum(r["aaa"] for r in rows)/len(rows),1),
         "en_iyi_aaa":rows[0]["aaa"] if rows else 0,
         "en_kotu_aaa":rows[-1]["aaa"] if rows else 0,
         "en_iyiler":best}
    Path("studio/autopilot/_aaa.json").write_text(json.dumps(rep,indent=1,ensure_ascii=False),encoding="utf-8")
    print(f"AAA_DONE taranan={len(rows)} ort={rep['ort_aaa']} en_iyi={rep['en_iyi_aaa']} -> {OUT}/")

main()
