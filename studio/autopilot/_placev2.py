import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_pv2.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
rc("execute_menu_item", {"path":"Assets/Refresh"}, 30); time.sleep(7); fresh()
# eski/dagimik kaleyi sil
for _ in range(4): rc("delete_object", {"name":"GothicCastle"}, 12)
kp=(-482,95,-311)
r = rc("place_asset_on_terrain", {"asset_path":"Assets/Art/HQ/CastleV2.fbx",
    "x":kp[0],"z":kp[2],"scale":2.2,"name":"GothicCastle",
    "min_surface_y":0.0,"max_slope_deg":89.0,"search_radius":0.0,"y_offset":-1.5}, 120)
out.append("place="+json.dumps(r)[:120])
if isinstance(r,dict) and r.get("ok"):
    rc("set_rotation", {"name":"GothicCastle","x":-90,"y":0,"z":0}, 12)
    am = rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_CastleStone.mat",
        "name_contains":"GothicCastle","recurse":True}, 60)
    out.append("mat="+json.dumps(am)[:110])
    np=(r or {}).get("position") or {}; nx=float(np.get("x",kp[0])); nz=float(np.get("z",kp[2])); ny=float((r or {}).get("surface_y",kp[1]))
    rc("set_position", {"name":"LightBeam","x":nx,"y":ny+150,"z":nz}, 12)
out.append("saved="+str(save()))
# net kareler (2 aci)
for tag,yaw in [("v2_a",220),("v2_b",300)]:
    rc("set_scene_view", {"target":"GothicCastle","pitch":9,"yaw":yaw}, 30)
    time.sleep(1.2)
    from ap import _studio_shot
    _studio_shot(name=tag)
out.append("shots v2_a/b")
Path("studio/autopilot/_pv2.txt").write_text("\n".join(out), encoding="utf-8")
