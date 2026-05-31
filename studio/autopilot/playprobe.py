"""Play'e gir, BootProbe'un dosya yazmasi icin 8 sn TAM bekle, sonra cik.
Sonuc dosyasi: UnityProject/bootprobe_result.txt (BootProbe yazar)."""
import sys, time, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *

PROBE = "C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject/bootprobe_result.txt"
connect()
guard_scene()
save()
try: os.remove(PROBE)
except Exception: pass

log = []
pr = rc("play_mode", {"play": True}, 40)
log.append("enter=" + json.dumps(pr)[:60])
# 8 sn boyunca her 2 sn'de is_playing + probe dosyasi kontrol; cikma!
got = False
for i in range(4):
    time.sleep(2); fresh()
    es = rc("get_editor_state", {}, 15) or {}
    exists = os.path.exists(PROBE)
    log.append(f"t{(i+1)*2}s: is_playing={es.get('is_playing')} probe={exists}")
    if exists:
        got = True
        break
fresh()
rc("play_mode", {"play": False}, 40)
time.sleep(2)
log.append("probe_written=" + str(got or os.path.exists(PROBE)))
Path("studio/autopilot/_playprobe.txt").write_text("\n".join(log), encoding="utf-8")
print("PROBE_RUN_DONE")
