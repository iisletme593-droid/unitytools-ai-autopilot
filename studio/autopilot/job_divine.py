"""Ilahi isik huzmesi: kaleye gokten inen sicak isik sutunu (mesh) + DivineLight
guclendir. Geri alinabilir (DivineBeam silinebilir). Play KAPALI; gorsel dogrula."""
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
ks = ap.pos_of("GothicCastle") or (-482, 146, -311)
# huzme mesh: ince uzun silindir, kaleden goge, hafif egik
for _ in range(2): ap.rc("delete_object", {"name": "DivineBeam"}, 8)
ap.rc("create_primitive", {"type": "Cylinder", "name": "DivineBeam",
      "position": {"x": ks[0], "y": ks[1] + 55, "z": ks[2]},
      "scale": {"x": 11, "y": 55, "z": 11}}, 18)
ap.rc("set_rotation", {"name": "DivineBeam", "x": 8, "y": 0, "z": 6}, 12)
# sicak parlak (matte = duzgun aydinlik sutun)
ap.color("DivineBeam", 1.0, 0.93, 0.74, smooth=0.0)
# DivineLight'i guclendir (kaleye sicak ilahi parilti)
ap.rc("set_light_properties", {"name": "DivineLight", "intensity": 9000,
      "range": 120, "color": {"r": 1.0, "g": 0.9, "b": 0.72}}, 15)
out.append("beam+light kuruldu")
out.append("SAVE=" + str(ap.save())[:8])
# dogrula: kaleyi hedefle
ap.rc("set_scene_view", {"target": "GothicCastle", "size": 170, "pitch": 6, "yaw": 40}, 30)
time.sleep(1.4)
sh = ap._studio_shot(name="divine_check") or {}
f = str(Path(os.getcwd()) / sh.get("path", ""))
a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
h, w, _ = a.shape; lum = 0.299*a[...,0]+0.587*a[...,1]+0.114*a[...,2]
col = lum.mean(0); peak = float(col.max()); med = float(np.median(col))
out.append("huzme_orani=%.2f peak=%.0f med=%.0f konum=%.2f" % ((peak-med)/max(med,1), peak, med, float(np.argmax(col))/w))
out.append("file=" + f)
Path("studio/autopilot/_divine.txt").write_text("\n".join(out), encoding="utf-8")
print("DIVINE_DONE")
