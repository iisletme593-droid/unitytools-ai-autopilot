"""KARE ELEME v2 (3000 olcekli): binlerce PNG'yi sayisal analiz eder, NEAR-DUPLICATE
kareleri perceptual-hash ile atar, CESITLILIK kovalarina boler, ve LLM'e (bana)
sadece en kritik + en CESITLI ~24 kareyi getirir.

Neden v2: v1 top-N-by-score yapinca 6 tane neredeyse AYNI karanlik kareyi
donduruyordu (parlaklik 3-6 hepsi). v2 dHash ile tekrarlari eler -> her secilen
kare GERCEKTEN farkli bir sey gosterir. 3000 kareyi de saniyeler icinde isler
(LLM yok, saf numpy).

Metrikler: brightness, blown(yikanma), crushed(karanlik), black_block(siyah blok),
green, sky, sharp(detay), problem_score.

Kullanim: python shot_triage.py [png_klasoru] [top_problem=14] [top_good=8]
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
TOP_PROBLEM = int(sys.argv[2]) if len(sys.argv) > 2 else 14
TOP_GOOD    = int(sys.argv[3]) if len(sys.argv) > 3 else 8
REVIEW = "studio/autopilot/review"

def dhash(gray64):
    # 9x8 difference hash -> 64-bit perceptual imza (near-duplicate tespiti)
    g = np.asarray(Image.fromarray(gray64.astype('uint8')).resize((9, 8)))
    bits = g[:, 1:] > g[:, :-1]
    h = 0
    for b in bits.flatten():
        h = (h << 1) | int(b)
    return h

def hamming(a, b):
    return bin(a ^ b).count("1")

def analyze(path):
    im = Image.open(path).convert("RGB"); im.thumbnail((256, 256))
    a = np.asarray(im).astype(np.int32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = 0.299*r + 0.587*g + 0.114*b
    mx = a.max(2); mn = a.min(2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    L = lum
    lap = np.abs(4*L[1:-1,1:-1]-L[:-2,1:-1]-L[2:,1:-1]-L[1:-1,:-2]-L[1:-1,2:])
    m = {
        "brightness": round(float(lum.mean()), 1),
        "blown":   round(float((lum > 250).mean()), 3),
        "crushed": round(float((lum < 12).mean()), 3),
        "black_block": round(float(((lum < 70) & (sat < 0.18)).mean()), 3),
        "green":   round(float(((g > r) & (g > b) & (g > 45)).mean()), 3),
        "sky":     round(float(((b > r) & (b > 110)).mean()), 3),
        "sharp":   round(float(lap.var()), 1),
        "_hash":   dhash(lum),
    }
    s = 0.0
    s += max(0, m["blown"]-0.04) * 120
    s += max(0, m["crushed"]-0.30) * 60
    s += max(0, m["black_block"]-0.20) * 80
    if m["sharp"] < 80: s += (80-m["sharp"])*0.4
    if m["brightness"] < 35 or m["brightness"] > 200: s += 25
    m["problem_score"] = round(s, 1)
    return m

def pick_diverse(rows, n, key, min_ham=12):
    """key'e gore sirala, ama near-duplicate (hamming<min_ham) olanlari atla."""
    rows = sorted(rows, key=key)
    out = []
    for r in rows:
        if all(hamming(r["_hash"], o["_hash"]) >= min_ham for o in out):
            out.append(r)
        if len(out) >= n:
            break
    return out

def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.png")), key=os.path.getmtime)
    if not files:
        print("KARE YOK:", SRC); return
    rows = []
    for f in files:
        try:
            m = analyze(f); m["file"] = f; rows.append(m)
        except Exception:
            pass
    probs = pick_diverse([r for r in rows if r["problem_score"] > 12],
                         TOP_PROBLEM, key=lambda x: -x["problem_score"])
    goods = pick_diverse([r for r in rows if r["problem_score"] < 8
                          and r["sharp"] > 120 and 55 < r["brightness"] < 195],
                         TOP_GOOD, key=lambda x: -x["sharp"])

    Path(REVIEW).mkdir(parents=True, exist_ok=True)
    for old in glob.glob(os.path.join(REVIEW, "*.png")): os.remove(old)
    picked = []
    def emit(rs, tag):
        for i, r in enumerate(rs):
            dst = os.path.join(REVIEW, f"{tag}_{i:02d}.png")
            Image.open(r["file"]).convert("RGB").resize((400,225)).save(dst)
            picked.append({"tag":tag,"review":dst,"src":os.path.basename(r["file"]),
                           **{k:r[k] for k in ("problem_score","brightness","blown",
                              "crushed","black_block","green","sky","sharp")}})
    emit(probs, "PROBLEM"); emit(goods, "GOOD")

    rep = {"taranan": len(rows), "secilen": len(picked),
           "ozet": {
               "ort_parlaklik": round(sum(r["brightness"] for r in rows)/len(rows),1),
               "yikanmis": sum(1 for r in rows if r["blown"]>0.06),
               "karanlik": sum(1 for r in rows if r["crushed"]>0.4),
               "siyahblok": sum(1 for r in rows if r["black_block"]>0.25),
               "iyi_aday": sum(1 for r in rows if r["problem_score"]<8 and r["sharp"]>120),
           },
           "secilenler": picked}
    Path("studio/autopilot/_triage.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"TRIAGE2_DONE taranan={len(rows)} secilen={len(picked)} (cesitli) -> {REVIEW}/")

main()
