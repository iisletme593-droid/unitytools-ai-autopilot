import sys, json, math; from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# agac konumlarini topla, en yogun + DUZ bolgeyi bul
r=rc("find_scene_objects",{"name_contains":"Tree_","max_count":2000},90) or {}
pts=[]
for o in (r.get("objects") or []):
    if not isinstance(o,dict) or "Tree_" not in str(o.get("name","")): continue
    p=o.get("position") or {}
    x,y,z=p.get("x"),p.get("y"),p.get("z")
    if x is None: continue
    pts.append((float(x),float(y),float(z)))
# 60m hucrelerde say + ortalama yukseklik (duz = dusuk std)
cell=60.0; buck=defaultdict(list)
for x,y,z in pts:
    buck[(math.floor(x/cell),math.floor(z/cell))].append((x,y,z))
ranked=[]
for k,v in buck.items():
    if len(v)<8: continue
    ys=[p[1] for p in v]; ymin=min(ys); ymax=max(ys)
    cx=sum(p[0] for p in v)/len(v); cz=sum(p[2] for p in v)/len(v); cy=sum(ys)/len(ys)
    ranked.append((len(v), ymax-ymin, round(cx),round(cy),round(cz)))
# once yogunluk, sonra duzluk
ranked.sort(key=lambda t:(-t[0], t[1]))
out=["en yogun 6 agac bolgesi (sayi, yukseklik_farki, x,y,z):"]
for t in ranked[:6]:
    out.append(f"  {t[0]} agac, dY={t[1]:.0f}m @ ({t[3]},{t[4]},{t[5]})")
out.append(f"toplam agac noktasi: {len(pts)}")
out.append(f"kamp konumu: {pos_of('Campfire')}")
Path("studio/autopilot/_tz.txt").write_text("\n".join(out), encoding="utf-8")
