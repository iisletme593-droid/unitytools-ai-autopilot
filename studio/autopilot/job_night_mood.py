"""Karanlik-fantezi alacakaranlik atmosferi (referans gorsellerin havasi):
soguk yogun sis, dusuk gunes acisi + soguk renk, soguk ambient, kamp ateşi
sicakligi one ciksin. Sonra dogrulama ekran goruntusu."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *

connect()
if not guard_scene():
    Path("studio/autopilot/_night.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit

out = []
# tek gunes: alcak aci (alacakaranlik) + soguk-mavi ton
L = rc("list_lights", {}, 15) or {}
arr = L.get("lights") or []
suns = [x for x in arr if "sun" in str(x.get("name","")).lower()
        or str(x.get("type","")).lower().startswith("dir")]
# fazla gunesleri temizle, tek birak
for s in suns[1:]:
    rc("delete_object", {"name": s.get("name")}, 10)
nm = suns[0].get("name") if suns else "Sun1"
if not suns:
    rc("create_light", {"light_type":"Directional","name":nm,"intensity":100000,
        "color":{"r":0.6,"g":0.68,"b":0.85}}, 18)
rc("set_light_properties", {"name":nm,"intensity":42000,
    "color":{"r":0.62,"g":0.68,"b":0.85},"shadows_enabled":True}, 15)
rc("set_rotation", {"name":nm,"x":8,"y":-24,"z":0}, 12)   # alcak, yatay isik
out.append("sun=" + nm)

# soguk yogun sis + dusuk pozlama (HDRP: dusuk EV = parlak; gece icin biraz yukselt)
rc("setup_hdrp_volume", {"fog":True,"fog_distance":200.0,
    "exposure_mode":"Fixed","fixed_exposure":12.6}, 20)
out.append("fog+exposure ok")

# kamp ateşi sicakligini guclendir (varsa)
if pos_of("CampfireLight"):
    rc("set_light_properties", {"name":"CampfireLight","intensity":220.0,
        "color":{"r":1.0,"g":0.5,"b":0.2}}, 12)
    out.append("campfire boosted")

out.append("saved=" + str(save()))

# dogrulama: kamptan genel kare
cf = pos_of("Campfire") or pos_of("WoodHouse", -533,138,-105)
p = shot("night_mood", cf[0]+22, cf[1]+16, cf[2]+22, 75, 12, 210)
out.append("shot=" + p)
Path("studio/autopilot/_night.txt").write_text("\n".join(out), encoding="utf-8")
print("NIGHT_DONE")
