import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
L=rc("list_lights",{},15) or {}
arr=L.get("lights") or []
out=[f"toplam isik={len(arr)}"]
for x in arr:
    t=str(x.get("type","?")); nm=str(x.get("name","?")); I=x.get("intensity")
    out.append(f"  {nm} type={t} I={I}")
Path("studio/autopilot/_exp2.txt").write_text("\n".join(out), encoding="utf-8")
