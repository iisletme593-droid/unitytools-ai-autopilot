import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out={}
for nm in ["Campfire","CampSite","SK_Hero","WorldForestGLB","RumorBoard","CraftStation","PlayerSpawn"]:
    p=pos_of(nm)
    out[nm]=[round(v) for v in p] if p else None
# kamp yaninda DUZ bir nokta (ev icin) + biraz uzakta tepe (kale icin)
cf=pos_of("Campfire") or (-526,142,-98)
# ev: kampın 15m yaninda yuzey
ev=surf(cf[0]+15, cf[2]+8, cf[1]); out["ONERI_ev"]=[round(cf[0]+15),round(ev),round(cf[2]+8)]
# kale: kampın 70m kuzeyinde yuzey
kale=surf(cf[0]+10, cf[2]-70, cf[1]); out["ONERI_kale"]=[round(cf[0]+10),round(kale),round(cf[2]-70)]
Path("studio/autopilot/_coords.txt").write_text(json.dumps(out,ensure_ascii=False), encoding="utf-8")
