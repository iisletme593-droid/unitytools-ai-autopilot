import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene(); save()
out=[]
pr = rc("play_mode", {"play": True}, 40)
out.append("enter="+json.dumps(pr)[:60])
time.sleep(7); fresh()
es = rc("get_editor_state", {}, 15) or {}
out.append("is_playing="+str(es.get("is_playing")))
# Play'de oyuncu + HUD runtime'da var mi?
for nm in ["SK_Hero","TI_HUD"]:
    d=rc("get_object_details",{"name":nm},12) or {}
    out.append(f"{nm}_runtime="+("OK" if d.get("name") else "YOK"))
fresh(); rc("play_mode", {"play": False}, 40); time.sleep(2)
out.append("exited")
Path("studio/autopilot/_pv.txt").write_text("\n".join(out), encoding="utf-8")
