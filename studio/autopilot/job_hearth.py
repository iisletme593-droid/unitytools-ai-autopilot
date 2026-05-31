"""OCAK SICAK HAVUZ — art_bible #1 aksan: 'safe-warm hearth vs wild-cold'.
Referansin duygusal merkezi. Dusuk riskli, sayisal dogrulanabilir (atese yakin
sicak-piksel orani artmali). Play KAPALI.
- CampfireLight: guclu sicak point (amber), makul menzil
- ates cekirdegine emissive kor (bloom yakalar)
- ev penceresine kucuk sicak isik (yasanmislik)
"""
import sys, time, os
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
cf = ap.pos_of("Campfire") or (-526, 142, -98)

# ocak isigi: guclu sicak point
for _ in range(2): ap.rc("delete_object", {"name": "CampfireLight"}, 8)
ap.rc("create_light", {"light_type": "Point", "name": "CampfireLight",
      "intensity": 900, "range": 22, "color": {"r": 1.0, "g": 0.52, "b": 0.2},
      "position": {"x": cf[0], "y": cf[1]+1.6, "z": cf[2]}}, 18)
ap.rc("set_parent", {"child": "CampfireLight", "parent": "Campfire"}, 10)
out.append("CampfireLight kuruldu")

# ates kor: kucuk emissive kure (bloom)
for _ in range(2): ap.rc("delete_object", {"name": "HearthEmber"}, 8)
ap.rc("create_primitive", {"type": "Sphere", "name": "HearthEmber",
      "position": {"x": cf[0], "y": cf[1]+0.6, "z": cf[2]},
      "scale": {"x": 1.4, "y": 1.0, "z": 1.4}}, 18)
ap.rc("set_material_color", {"name": "HearthEmber", "r": 1.0, "g": 0.55, "b": 0.2, "a": 1.0}, 12)
ap.rc("set_material_pbr", {"name": "HearthEmber", "metallic": 0.0, "smoothness": 0.0,
      "emission_enabled": True, "emission_color": {"r": 1.0, "g": 0.45, "b": 0.15},
      "emission_intensity": 9.0}, 15)
ap.rc("set_parent", {"child": "HearthEmber", "parent": "Campfire"}, 10)
out.append("HearthEmber kuruldu")

# ev penceresi sicak isik (yasanmislik)
wh = ap.pos_of("WoodHouse")
if wh:
    for _ in range(2): ap.rc("delete_object", {"name": "WindowGlow"}, 8)
    ap.rc("create_light", {"light_type": "Point", "name": "WindowGlow",
          "intensity": 240, "range": 10, "color": {"r": 1.0, "g": 0.66, "b": 0.32},
          "position": {"x": wh[0], "y": wh[1]+2.5, "z": wh[2]}}, 18)
    out.append("WindowGlow kuruldu")

out.append("SAVE=" + str(ap.save())[:8])

# DOGRULA: atese yakin sicak-piksel orani
ap.rc("set_scene_view", {"pivot_x": cf[0]+5, "pivot_y": cf[1]+2, "pivot_z": cf[2]+5,
                          "size": 16, "pitch": 6, "yaw": 45}, 25)
time.sleep(1.4)
sh = ap._studio_shot(name="hearth_check") or {}
f = str(Path(os.getcwd()) / sh.get("path", ""))
a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
rr, g, b = a[...,0], a[...,1], a[...,2]
lum = 0.299*rr+0.587*g+0.114*b
warm = float(((rr > 150) & (rr > g+25) & (g > b)).mean())  # sicak amber piksel
out.append("HEARTH sicak_oran=%.3f parl=%.0f" % (warm, lum.mean()))
out.append("file=" + f)
Path("studio/autopilot/_hearth.txt").write_text("\n".join(out), encoding="utf-8")
print("HEARTH_DONE")
