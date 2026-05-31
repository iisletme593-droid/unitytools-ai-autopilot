"""Play modu bu otomasyon ortaminda gercekten basliyor mu?
Enter play -> 12 sn boyunca her 2 sn'de is_playing kontrol -> exit play.
Sonuc: studio/autopilot/_playdiag.txt
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *

connect()
guard_scene()
save()
log = []
pr = rc("play_mode", {"play": True}, 40)
log.append("enter=" + json.dumps(pr)[:80])
playing_seen = False
for i in range(6):
    time.sleep(2); fresh()
    es = rc("get_editor_state", {}, 15) or {}
    p = es.get("is_playing")
    log.append(f"t{(i+1)*2}s: is_playing={p}")
    if p:
        playing_seen = True
        break
fresh()
rc("play_mode", {"play": False}, 40)
time.sleep(2)
log.append("playing_seen=" + str(playing_seen))
Path("studio/autopilot/_playdiag.txt").write_text("\n".join(log), encoding="utf-8")
print("DIAG_DONE playing_seen=" + str(playing_seen))
