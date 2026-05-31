import sys, json, math; from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# 1848 agacin konumlari -> en yogun + duz 50m hucre
r=rc("find_scene_objects",{"name_contains":"Tree_","max_count":2000},90) or {}
pts=[]
for o in (r.get("objects") or []):
    if not isinstance(o,dict) or "Tree_" not in str(o.get("name","")): continue
    p=o.get("position") or {}
    if p.get("x") is None: continue
    pts.append((float(p["x"]),float(p["y"]),float(p["z"])))
cell=50.0; buck=defaultdict(list)
for x,y,z in pts:
    buck[(math.floor(x/cell),math.floor(z/cell))].append((x,y,z))
ranked=[]
for k,v in buck.items():
    if len(v)<10: continue
    ys=[p[1] for p in v]; dY=max(ys)-min(ys)
    cx=sum(p[0] for p in v)/len(v); cz=sum(p[2] for p in v)/len(v); cy=sum(ys)/len(ys)
    # yogunluk yuksek + duz (dY dusuk) skoru
    ranked.append((len(v)-dY*0.5, len(v), round(dY), round(cx), round(cy), round(cz)))
ranked.sort(reverse=True)
top=[{"agac":t[1],"dY":t[2],"x":t[3],"y":t[4],"z":t[5]} for t in ranked[:5]]
Path("studio/autopilot/_dense.txt").write_text(json.dumps({"toplam":len(pts),"top":top}), encoding="utf-8")
