import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_hm.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
ps = pos_of("PlayerSpawn")
out=[]
if ps:
    x,y,z = ps
    # CharacterController'i gecici kapatip tasimak guvenli degil bridge'den;
    # set_position dene (controller pozisyonu ezebilir ama sahnede kayitli kalir)
    r = rc("set_position", {"name":"SK_Hero","x":x,"y":y,"z":z}, 15)
    out.append(f"moved SK_Hero -> {x:.0f},{y:.0f},{z:.0f} ok={isinstance(r,dict)}")
else:
    out.append("PlayerSpawn YOK, tasima atlandi")
# Player tag dene (yoksa hata -> yut)
tr = rc("set_tag", {"name":"SK_Hero","tag":"Player"}, 12)
out.append("tag_set=" + json.dumps(tr)[:80])
d = rc("get_object_details", {"name":"SK_Hero"}, 15) or {}
out.append("now: pos="+str(d.get("position"))+" tag="+str(d.get("tag")))
out.append("saved="+str(save()))
Path("studio/autopilot/_hm.txt").write_text("\n".join(out), encoding="utf-8")
