import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
PROJ="C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject"
connect()
if not guard_scene():
    Path("studio/autopilot/_wirehero.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
# 1) SK_Hero modelini PlayerSpawn'a yerlestir (zaten projede import'lu)
ps = pos_of("PlayerSpawn") or (-529,143,-101)
HERO_SRC = f"{PROJ}/Assets/Art/Characters/Imported/Hero/SK_Hero.fbx"
imp = rc("import_asset", {"src_path": HERO_SRC, "dst_relative": "Art/HQ/SK_Hero.fbx"}, 90)
out.append("import="+json.dumps(imp)[:60])
import time as _t; _t.sleep(2); fresh()
r = rc("place_asset_on_terrain", {"asset_path":"Assets/Art/HQ/SK_Hero.fbx",
    "x":ps[0],"z":ps[2],"scale":1.0,"name":"SK_Hero","min_surface_y":0.0,
    "max_slope_deg":89.0,"search_radius":0.0,"y_offset":0.0}, 90)
out.append("place="+json.dumps(r)[:120])
# FBX Z-up -> dik dur
rc("set_rotation", {"name":"SK_Hero","x":-90,"y":0,"z":0}, 12)
out.append("hero_pos="+str(pos_of("SK_Hero")))
out.append("saved="+str(save()))
Path("studio/autopilot/_wirehero.txt").write_text("\n".join(out), encoding="utf-8")
