"""Huzmeyi zarif yap: daha ince + daha uzun + dramatik egim. Ayrica ikinci genis
soluk hare (halo) ekle. Gorsel dogrula."""
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
# ince ana huzme
ap.rc("set_scale", {"name": "DivineBeam", "x": 5.5, "y": 70, "z": 5.5}, 12)
ap.rc("set_position", {"name": "DivineBeam", "x": ks[0], "y": ks[1] + 70, "z": ks[2]}, 12)
ap.rc("set_rotation", {"name": "DivineBeam", "x": 10, "y": 0, "z": 7}, 12)
ap.color("DivineBeam", 1.0, 0.94, 0.78, smooth=0.0)
# genis soluk halo (ikinci silindir, daha mat/sicak)
for _ in range(2): ap.rc("delete_object", {"name": "DivineHalo"}, 8)
ap.rc("create_primitive", {"type": "Cylinder", "name": "DivineHalo",
      "position": {"x": ks[0], "y": ks[1] + 70, "z": ks[2]},
      "scale": {"x": 16, "y": 68, "z": 16}}, 18)
ap.rc("set_rotation", {"name": "DivineHalo", "x": 10, "y": 0, "z": 7}, 12)
ap.color("DivineHalo", 0.95, 0.86, 0.62, smooth=0.0)
out.append("SAVE=" + str(ap.save())[:8])
ap.rc("set_scene_view", {"target": "GothicCastle", "size": 165, "pitch": 6, "yaw": 40}, 30)
time.sleep(1.4)
sh = ap._studio_shot(name="divine2") or {}
f = str(Path(os.getcwd()) / sh.get("path", ""))
a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
h, w, _ = a.shape; lum = 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
col = lum.mean(0); peak = float(col.max()); med = float(np.median(col))
out.append("huzme=%.2f peak=%.0f med=%.0f" % ((peak-med)/max(med,1), peak, med))
out.append("file=" + f)
Path("studio/autopilot/_divine2.txt").write_text("\n".join(out), encoding="utf-8")
print("DIVINE2_DONE")
