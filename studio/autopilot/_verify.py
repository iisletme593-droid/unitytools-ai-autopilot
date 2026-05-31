import sys, time, os, json, glob
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
cf = ap.pos_of("Campfire") or (-526, 142, -98)
# kus bakisi cekirdek (cim yogunlugu)
ap.rc("set_scene_view", {"pivot_x": cf[0], "pivot_y": cf[1], "pivot_z": cf[2],
                          "size": 26, "pitch": 78, "yaw": 0}, 25)
time.sleep(1.4)
r = ap._studio_shot(name="bird_core") or {}
bird = str(Path(os.getcwd()) / r.get("path", ""))

def an(f):
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    h, w, _ = a.shape; rr, g, b = a[...,0], a[...,1], a[...,2]
    lum = 0.299*rr+0.587*g+0.114*b
    green = float(((g > rr+8) & (g > b+8)).mean())
    grey = float(((np.abs(rr-g) < 14) & (np.abs(g-b) < 14) & (rr > 55) & (rr < 175)).mean())
    return {"green": round(green,3), "bare_grey": round(grey,3), "parl": round(float(lum.mean()),1)}

res = {}
for f in sorted(glob.glob("studio/qa/screenshots/20260530_1504*.png")):
    res[os.path.basename(f)] = an(f)
res["bird_core_" + os.path.basename(bird)] = an(bird)
Path("studio/autopilot/_verify.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("VERIFY_DONE bird=" + bird)
