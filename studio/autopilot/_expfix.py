import sys, time, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# mevcut isik durumu
L=rc("list_lights",{},15) or {}
arr=L.get("lights") or []
dirs=[x for x in arr if str(x.get("type","")).lower().startswith("dir") or "sun" in str(x.get("name","")).lower()]
info={"gunes_sayisi":len(dirs),"gunes":[{"ad":x.get("name"),"I":x.get("intensity")} for x in dirs[:6]]}
Path("studio/autopilot/_exp.txt").write_text(json.dumps(info), encoding="utf-8")
