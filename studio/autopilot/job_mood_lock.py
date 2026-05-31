"""Mood kilitle: EV 12.0 (parl ~95 moody-okunabilir). Sonra 3 anahtar establishing
karesi al + JPEG'e cevir (gorus testi). Play KAPALI."""
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
ap.rc("setup_hdrp_volume", {"fog": True, "fog_distance": 440.0,
      "exposure_mode": "Fixed", "fixed_exposure": 12.0}, 30)
ap.fresh()
out.append("SAVE=" + str(ap.save())[:8])

cf = ap.pos_of("Campfire") or (-526, 142, -98)
ks = ap.pos_of("GothicCastle") or (-482, 146, -311)
views = [
    ("LOCK_hero", cf[0], cf[1]+8, cf[2], 70, 8, 200),
    ("LOCK_castle", (cf[0]+ks[0])/2, ks[1]+8, (cf[2]+ks[2])/2, 150, 7, 30),
    ("LOCK_eye", cf[0]+6, cf[1]+1.7, cf[2]+6, 18, 5, 50),
]
def met(f):
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    h, w, _ = a.shape; rr, g, b = a[...,0], a[...,1], a[...,2]
    lum = 0.299*rr+0.587*g+0.114*b
    return "parl=%.0f yesil=%.2f soguk=%.2f" % (lum.mean(),
           ((g>rr+8)&(g>b+8)).mean(), (b>rr).mean())
for name, px, py, pz, size, pitch, yaw in views:
    ap.rc("set_scene_view", {"pivot_x": px, "pivot_y": py, "pivot_z": pz,
                              "size": size, "pitch": pitch, "yaw": yaw}, 25)
    time.sleep(1.4)
    sh = ap._studio_shot(name=name) or {}
    f = str(Path(os.getcwd()) / sh.get("path", ""))
    jpg = f"studio/autopilot/_view_{name}.jpg"
    Image.open(f).convert("RGB").save(jpg, quality=84)
    out.append(f"{name} {met(f)} jpg={jpg}")
Path("studio/autopilot/_lock.txt").write_text("\n".join(out), encoding="utf-8")
print("LOCK_DONE")
