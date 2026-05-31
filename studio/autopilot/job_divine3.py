"""Huzme v3: sisman halo'yu sil, ince EMISSIVE (parlayan) sutun -> HDRP bloom ile
yumusak god-ray hissi. Emission set_material_pbr ile (bridge destekliyor)."""
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
ks = ap.pos_of("GothicCastle") or (-482, 146, -311)
out = []
# sisman halo'yu kaldir
for _ in range(3): ap.rc("delete_object", {"name": "DivineHalo"}, 8)
# ince sutun
ap.rc("set_scale", {"name": "DivineBeam", "x": 3.5, "y": 78, "z": 3.5}, 12)
ap.rc("set_position", {"name": "DivineBeam", "x": ks[0], "y": ks[1] + 78, "z": ks[2]}, 12)
ap.rc("set_rotation", {"name": "DivineBeam", "x": 9, "y": 0, "z": 6}, 12)
ap.rc("set_material_color", {"name": "DivineBeam", "r": 1.0, "g": 0.95, "b": 0.82, "a": 1.0}, 12)
# EMISSIVE -> bloom god-ray
r = ap.rc("set_material_pbr", {"name": "DivineBeam", "metallic": 0.0, "smoothness": 0.0,
          "emission_enabled": True, "emission_color": {"r": 1.0, "g": 0.88, "b": 0.66},
          "emission_intensity": 14.0}, 15)
out.append("emission=" + str(r)[:70])
out.append("SAVE=" + str(ap.save())[:8])
ap.rc("set_scene_view", {"target": "GothicCastle", "size": 165, "pitch": 6, "yaw": 40}, 30)
time.sleep(1.4)
sh = ap._studio_shot(name="divine3") or {}
f = str(Path(os.getcwd()) / sh.get("path", ""))
a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
h, w, _ = a.shape; lum = 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
col = lum.mean(0); peak = float(col.max()); med = float(np.median(col))
out.append("huzme=%.2f peak=%.0f med=%.0f" % ((peak-med)/max(med,1), peak, med))
out.append("file=" + f)
Path("studio/autopilot/_divine3.txt").write_text("\n".join(out), encoding="utf-8")
print("DIVINE3_DONE")
