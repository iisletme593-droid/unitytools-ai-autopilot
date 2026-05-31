import json, glob, os
from pathlib import Path
from PIL import Image
import numpy as np
D = "D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/studio/qa/screenshots/"
fs = sorted(glob.glob(D + "*.png"), key=os.path.getmtime, reverse=True)[:2]
res = {"frames": []}
sigs = []
for f in fs:
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.float32)
    h, w, _ = a.shape; r, g, b = a[...,0], a[...,1], a[...,2]
    lum = 0.299*r+0.587*g+0.114*b
    sig = {"file": os.path.basename(f),
           "sky": round(float((lum > 200).mean()), 3),
           "green": round(float(((g > r+8) & (g > b+8)).mean()), 3),
           "parl": round(float(lum.mean()), 1),
           "top_parl": round(float(lum[:h//3].mean()), 1),
           "bot_parl": round(float(lum[2*h//3:].mean()), 1)}
    res["frames"].append(sig)
    sigs.append((sig["sky"], sig["parl"]))
if len(sigs) == 2:
    res["FARKLI_MI"] = abs(sigs[0][0]-sigs[1][0]) > 0.05 or abs(sigs[0][1]-sigs[1][1]) > 8
    res["sky_fark"] = round(abs(sigs[0][0]-sigs[1][0]), 3)
    res["parl_fark"] = round(abs(sigs[0][1]-sigs[1][1]), 1)
Path("studio/autopilot/_camdiff.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
print("CAMDIFF_DONE")
