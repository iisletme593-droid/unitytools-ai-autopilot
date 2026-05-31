import sys, json, math, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_comp.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
cf=pos_of("Campfire") or (-526,141,-98)
# kaleyi kamptan ~90m KUZEY'e (manzarada arkada gozuksun); duz-ish nokta ara
# kamp yonu: origin'e dogru degil, kuzeye (-z) tepeye
kx, kz = cf[0]+20, cf[2]-90
# kaleyi tasi (search ile yakin duz nokta)
r=rc("place_asset_on_terrain", {"asset_path":"Assets/Art/HQ/CastleV2.fbx",
    "x":kx,"z":kz,"scale":2.2,"name":"GothicCastle",
    "min_surface_y":5.0,"max_slope_deg":35.0,"search_radius":60.0,"y_offset":-1.5}, 120)
out.append("castle_place="+json.dumps(r)[:120])
if isinstance(r,dict) and r.get("ok"):
    rc("set_rotation", {"name":"GothicCastle","x":0,"y":0,"z":0}, 12)
    rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_CastleStone.mat","name_contains":"GothicCastle","recurse":True}, 60)
    np=(r or {}).get("position") or {}; nx=float(np.get("x",kx)); nz=float(np.get("z",kz)); ny=float((r or {}).get("surface_y",cf[1]))
    rc("set_position", {"name":"LightBeam","x":nx,"y":ny+140,"z":nz}, 12)
    out.append(f"yeni_kale=({nx:.0f},{ny:.0f},{nz:.0f}) mesafe={math.hypot(nx-cf[0],nz-cf[2]):.0f}m")
out.append("saved="+str(save()))
Path("studio/autopilot/_comp.txt").write_text("\n".join(out), encoding="utf-8")
