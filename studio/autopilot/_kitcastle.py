import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
PROJ="C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject"
connect()
if not guard_scene():
    Path("studio/autopilot/_kc.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
# eski kalenin yerini hatirla
kp = pos_of("GothicCastle") or (-482,95,-311)
out.append("eski_kale="+str(kp))
# import
imp = rc("import_asset", {"src_path": f"{PROJ}/studio/assets/hq/CastleKit/final.fbx",
    "dst_relative":"Art/HQ/CastleKit.fbx"}, 120)
out.append("import="+json.dumps(imp)[:70])
time.sleep(3); fresh()
# eski kaleyi sil
for _ in range(3): rc("delete_object", {"name":"GothicCastle"}, 12)
# yeni kaleyi ayni yere koy (FBX Z-up -> rotx -90), olcek dene 3.0
r = rc("place_asset_on_terrain", {"asset_path":"Assets/Art/HQ/CastleKit.fbx",
    "x":kp[0],"z":kp[2],"scale":3.0,"name":"GothicCastle",
    "min_surface_y":0.0,"max_slope_deg":89.0,"search_radius":0.0,"y_offset":-1.0}, 120)
out.append("place="+json.dumps(r)[:120])
rc("set_rotation", {"name":"GothicCastle","x":-90,"y":0,"z":0}, 12)
# gercek tas malzeme ata
am = rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_GothicStone.mat",
    "name_contains":"GothicCastle","recurse":True}, 60)
out.append("mat="+json.dumps(am)[:120])
# huzme kaleye
np=(r or {}).get("position") or {}; nx=float(np.get("x",kp[0])); nz=float(np.get("z",kp[2])); ny=float((r or {}).get("surface_y",kp[1]))
rc("set_position", {"name":"LightBeam","x":nx,"y":ny+150,"z":nz}, 12)
out.append("saved="+str(save()))
# bounds + kare
fr = rc("set_scene_view", {"target":"GothicCastle","pitch":7,"yaw":220}, 30)
out.append("bounds="+str(fr.get("size") if isinstance(fr,dict) else "?"))
time.sleep(1.2)
from ap import _studio_shot
_studio_shot(name="kitcastle")
out.append("shot=kitcastle")
Path("studio/autopilot/_kc.txt").write_text("\n".join(out), encoding="utf-8")
