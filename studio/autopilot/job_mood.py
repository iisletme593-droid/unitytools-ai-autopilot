"""SINEMATIK MOOD PASS — art_bible.md hedefi: parlak oglen -> soguk dark-fantasy.
- Gok: desatüre slate-mavi overcast (#3a4250), parlak cyan DEGIL
- Sis: kalin cool grey-blue volumetrik (#5a6470)
- Gunes: alcak aci (15deg) + sicak amber key + uzun golgeler
- Exposure: Fixed ~13.8 EV, ACES tonemap
Play KAPALI. Gorsel + sayisal dogrula (gok doygunlugu dusmeli, kare soguklasmali).
"""
import sys, time, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
from PIL import Image
import numpy as np

ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
out = []

# 1) EXPOSURE + ACES + volumetrik sis (tek volume)
r = ap.rc("setup_hdrp_volume", {"fog": True, "fog_distance": 250.0,
          "exposure_mode": "Fixed", "fixed_exposure": 13.9}, 30)
out.append("hdrp_volume=" + str(r.get("ok") if isinstance(r, dict) else r))

# 2) GOK: slate-mavi overcast (gradient sky + ambient)
r = ap.rc("set_skybox", {"color": "#3a4250", "intensity": 0.82}, 20)
out.append("sky=" + str(r.get("sky") if isinstance(r, dict) else r))

# 3) SIS: cool grey-blue, kalin (meanFreePath dusuk = yogun)
r = ap.rc("set_fog", {"fog_distance": 240.0, "color": "#5a6470"}, 20)
out.append("fog=" + str(r.get("ok") if isinstance(r, dict) else r))

# 4) GUNES: alcak + sicak + golge
L = ap.rc("list_lights", {}, 15) or {}
arr = L.get("lights") or []
sun = None
for x in arr:
    nm = str(x.get("name", "")).lower()
    if x.get("type") == "Directional" or "sun" in nm:
        sun = x.get("name"); break
if not sun:
    ap.rc("create_light", {"light_type": "Directional", "name": "Sun1",
          "intensity": 42000, "color": {"r": 1.0, "g": 0.84, "b": 0.6}}, 18)
    sun = "Sun1"
ap.rc("set_light_properties", {"name": sun, "intensity": 42000,
      "color": {"r": 1.0, "g": 0.84, "b": 0.6}, "shadows_enabled": True}, 15)
ap.rc("set_rotation", {"name": sun, "x": 15, "y": -42, "z": 0}, 12)
out.append("sun=" + str(sun) + " (alcak+sicak)")

out.append("SAVE=" + str(ap.save())[:8])

# DOGRULA: hero establishing (kaleye dogru, on planda kamp)
cf = ap.pos_of("Campfire") or (-526, 142, -98)
ks = ap.pos_of("GothicCastle") or (-482, 146, -311)
ap.rc("set_scene_view", {"pivot_x": cf[0], "pivot_y": cf[1]+8, "pivot_z": cf[2],
                          "size": 70, "pitch": 8, "yaw": 200}, 25)
time.sleep(1.5)
sh = ap._studio_shot(name="mood_hero") or {}
f = str(Path(os.getcwd()) / sh.get("path", ""))
a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
h, w, _ = a.shape; rr, g, b = a[...,0], a[...,1], a[...,2]
lum = 0.299*rr+0.587*g+0.114*b
sky_reg = a[:h//3]
sky_sat = float((np.max(sky_reg,2)-np.min(sky_reg,2)).mean())
cool = float((b > rr).mean())  # soguk piksel orani
out.append("MOOD parl=%.0f gok_doygunluk=%.0f soguk_oran=%.2f" % (lum.mean(), sky_sat, cool))
out.append("file=" + f)
Path("studio/autopilot/_mood.txt").write_text("\n".join(out), encoding="utf-8")
print("MOOD_DONE")
