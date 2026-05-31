"""Kale + kuleleri zemine oturt: bbox taban 124.8, gercek zemin 142.6 -> 17.8m
gomulu. Kale pivot + CastleSpires grubunu birlikte kaldir, taban zemin-0.6'ya
otursun. Tek temiz sayiyla dogrula. Play KAPALI."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()

gc = ap.rc("get_object_details", {"name": "GothicCastle"}, 18) or {}
p = gc.get("position") or {}
wb = gc.get("world_bounds") or {}; c = wb.get("center", {}); s = wb.get("size", {})
base = c.get("y", 0) - s.get("y", 0) / 2.0
terr = ap.surf(p.get("x", -482) + 70, p.get("z", -311), 142)  # gercek zemin (uzak)
SINK = 0.6
lift = (terr - SINK) - base          # tabani zemine getirecek delta
new_castle_y = p.get("y", 94.4) + lift

ap.rc("set_position", {"name": "GothicCastle", "x": p.get("x"), "y": new_castle_y, "z": p.get("z")}, 15)
# kuleleri ayni delta ile
sp = ap.rc("get_object_details", {"name": "CastleSpires"}, 12) or {}
spp = sp.get("position") or {}
if sp.get("name"):
    ap.rc("set_position", {"name": "CastleSpires", "x": spp.get("x"),
          "y": spp.get("y", 0) + lift, "z": spp.get("z")}, 15)
# DivineBeam de kaleyle yuksel (huzme kaleden ciksin) — sadece +lift degil, zaten
# kaleye gore konumlanmisti; dokunmuyoruz (gokte, sorun degil)

ap.save()
# dogrula
d2 = ap.rc("get_object_details", {"name": "GothicCastle"}, 18) or {}
wb2 = d2.get("world_bounds") or {}; c2 = wb2.get("center", {}); s2 = wb2.get("size", {})
base2 = c2.get("y", 0) - s2.get("y", 0) / 2.0
print("LIFT=%.1f YENI_TABAN=%.1f ZEMIN=%.1f GOMULME=%.1f" % (lift, base2, terr, terr - base2))
