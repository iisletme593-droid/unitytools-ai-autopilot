"""MOOD v2 — v1 cok karardi (parl 31). Art bible: overcast nordic, BOUNDED fog
(40-60m gorus), desature, alcak sicak gunes, tek sicak aksан (ocak). Duzelt:
- skybox sky_tint objesiyle (v1 color param'i tutmadi)
- fog gevset (mfp 450 - duvar degil)
- gunes 75k
- EXPOSURE SUPURMESI: 13.2/12.8/12.4 dene, parl~105'e en yakini sec
Play KAPALI."""
import sys, time, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
from PIL import Image
import numpy as np

def metrics(f):
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    h, w, _ = a.shape; rr, g, b = a[...,0], a[...,1], a[...,2]
    lum = 0.299*rr+0.587*g+0.114*b
    skreg = a[:h//3]
    return {"parl": round(float(lum.mean()),1),
            "gok_doy": round(float((np.max(skreg,2)-np.min(skreg,2)).mean()),1),
            "soguk": round(float((b > rr).mean()),2),
            "yesil": round(float(((g>rr+8)&(g>b+8)).mean()),2)}

ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
out = []

# skybox: slate-mavi overcast (procedural sky_tint + ground)
r = ap.rc("set_skybox", {"sky_tint": {"r": 0.42, "g": 0.47, "b": 0.55},
          "ground_color": {"r": 0.22, "g": 0.24, "b": 0.22},
          "atmosphere_thickness": 1.6, "exposure": 1.05, "sun_size": 0.02}, 20)
out.append("sky=" + str(r.get("mode") if isinstance(r, dict) else r))
# fog gevset (bounded, duvar degil): cool grey-blue
ap.rc("set_fog", {"enabled": True, "color": {"r": 0.42, "g": 0.47, "b": 0.54}}, 20)
# gunes guclendir
L = ap.rc("list_lights", {}, 15) or {}
sun = next((x.get("name") for x in (L.get("lights") or [])
            if x.get("type") == "Directional" or "sun" in str(x.get("name","")).lower()), "Sun1")
ap.rc("set_light_properties", {"name": sun, "intensity": 75000,
      "color": {"r": 1.0, "g": 0.86, "b": 0.64}, "shadows_enabled": True}, 15)
ap.rc("set_rotation", {"name": sun, "x": 16, "y": -44, "z": 0}, 12)

cf = ap.pos_of("Campfire") or (-526, 142, -98)
best = None
for ev, mfp in [(13.2, 500.0), (12.8, 450.0), (12.4, 420.0)]:
    ap.rc("setup_hdrp_volume", {"fog": True, "fog_distance": mfp,
          "exposure_mode": "Fixed", "fixed_exposure": ev}, 30)
    ap.fresh()
    ap.rc("set_scene_view", {"pivot_x": cf[0], "pivot_y": cf[1]+8, "pivot_z": cf[2],
                              "size": 70, "pitch": 8, "yaw": 200}, 25)
    time.sleep(1.4)
    sh = ap._studio_shot(name=f"mood2_ev{int(ev*10)}") or {}
    f = str(Path(os.getcwd()) / sh.get("path", ""))
    m = metrics(f); m["ev"] = ev; m["mfp"] = mfp; m["file"] = f
    out.append("EV%.1f mfp%.0f -> parl=%.0f gok_doy=%.0f soguk=%.2f yesil=%.2f" %
               (ev, mfp, m["parl"], m["gok_doy"], m["soguk"], m["yesil"]))
    if best is None or abs(m["parl"]-105) < abs(best["parl"]-105):
        best = m

# en iyi EV'yi uygula + kaydet
ap.rc("setup_hdrp_volume", {"fog": True, "fog_distance": best["mfp"],
      "exposure_mode": "Fixed", "fixed_exposure": best["ev"]}, 30)
ap.fresh()
out.append("SECILEN EV=%.1f mfp=%.0f parl=%.0f" % (best["ev"], best["mfp"], best["parl"]))
out.append("SAVE=" + str(ap.save())[:8])
out.append("best_file=" + best["file"])
Path("studio/autopilot/_mood2.txt").write_text("\n".join(out), encoding="utf-8")
print("MOOD2_DONE")
