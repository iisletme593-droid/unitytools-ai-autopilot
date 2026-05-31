"""Kale siluetini GOTIKlestir: bodur ModularFort'a (oran 0.70) sivri kuleler ekle.
Additive + geometrik dogrulanabilir (yeni bbox yuksekligi/orani). Tas malzeme
(HDRP_M_CastleStone) tekrar kullanilir, koni catili. Play KAPALI.
Gotik: 4 kose kulesi + 1 yuksek merkez kule, hepsi sivri koni catili."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import ap

STONE = "Assets/FantasyRPG/Generated/Materials/HDRP_M_CastleStone.mat"
ap.connect()
es = ap.rc("get_editor_state", {}, 15) or {}
if es.get("is_playing"):
    ap.rc("play_mode", {"play": False}, 40); time.sleep(2); ap.fresh()
ap.guard_scene()
out = []

d = ap.rc("get_object_details", {"name": "GothicCastle"}, 20) or {}
wb = d.get("world_bounds") or {}; c = wb.get("center", {}); s = wb.get("size", {})
cx, cz = c.get("x", -482), c.get("z", -311)
base_y = c.get("y", 142) - s.get("y", 36) / 2.0
foot = max(s.get("x", 50), s.get("z", 50))
half = foot * 0.42
out.append(f"merkez=({cx:.0f},{cz:.0f}) taban_y={base_y:.0f} ayak={foot:.0f}")

# grup
for _ in range(2): ap.rc("delete_object", {"name": "CastleSpires"}, 8)
ap.rc("create_empty", {"name": "CastleSpires", "position": {"x": cx, "y": base_y, "z": cz}}, 12)

def tower(nm, x, z, shaft_h, shaft_r, roof_h):
    # govde (silindir)
    ap.rc("create_primitive", {"type": "Cylinder", "name": nm + "_shaft",
          "position": {"x": x, "y": base_y + shaft_h/2, "z": z},
          "scale": {"x": shaft_r*2, "y": shaft_h/2, "z": shaft_r*2}}, 16)
    ap.rc("set_parent", {"child": nm + "_shaft", "parent": "CastleSpires"}, 10)
    # sivri cati (koni — yoksa silindir konik scale)
    rr = ap.rc("create_primitive", {"type": "Cone", "name": nm + "_roof",
          "position": {"x": x, "y": base_y + shaft_h + roof_h/2, "z": z},
          "scale": {"x": shaft_r*2.3, "y": roof_h/2, "z": shaft_r*2.3}}, 16)
    if not (isinstance(rr, dict) and rr.get("ok")):
        # Cone yoksa: ince uzun silindir cati taklidi
        ap.rc("create_primitive", {"type": "Cylinder", "name": nm + "_roof",
              "position": {"x": x, "y": base_y + shaft_h + roof_h/2, "z": z},
              "scale": {"x": shaft_r*0.6, "y": roof_h/2, "z": shaft_r*0.6}}, 16)
    ap.rc("set_parent", {"child": nm + "_roof", "parent": "CastleSpires"}, 10)
    # cati sicak-koyu kiremit
    ap.color(nm + "_roof", 0.20, 0.16, 0.18, smooth=0.1)

# 4 kose kulesi
corners = [("T_NE", cx+half, cz+half), ("T_NW", cx-half, cz+half),
           ("T_SE", cx+half, cz-half), ("T_SW", cx-half, cz-half)]
for nm, x, z in corners:
    tower(nm, x, z, shaft_h=46, shaft_r=4.5, roof_h=14)
# merkez yuksek kule (donjon)
tower("T_Keep", cx, cz, shaft_h=64, shaft_r=7.0, roof_h=22)
out.append("5 kule kuruldu")

# tas malzeme (govdelere)
ap.rc("assign_material_asset", {"material_path": STONE,
      "name_contains": "_shaft", "recurse": True}, 60)
out.append("SAVE=" + str(ap.save())[:8])

# DOGRULA: yeni birlesik bbox (kale + kuleler ayni merkezde)
d2 = ap.rc("get_object_details", {"name": "CastleSpires"}, 20) or {}
wb2 = d2.get("world_bounds") or {}; s2 = wb2.get("size", {})
sy2 = s2.get("y", 0); foot2 = max(s2.get("x", 1), s2.get("z", 1))
out.append("KULELER bbox=%.0fx%.0fx%.0f oran=%.2f (gotik hedef>1.2)" %
           (s2.get("x",0), sy2, s2.get("z",0), sy2/max(foot2,1)))
Path("studio/autopilot/_spires.txt").write_text("\n".join(out), encoding="utf-8")
print("SPIRES_DONE")
