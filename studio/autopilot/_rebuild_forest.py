import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# scatter_terrain_glb_trees ile ormani GERI getir (LP_Fir_GLB = alpha yok, koyu, blok degil)
# foliage malzeme = koyu yesil card needle (koyulastirilmis)
res=rc("scatter_terrain_glb_trees", {
    "models":["Assets/Art/HQ/LP_Fir_GLB.glb"],
    "dead_models":["Assets/Art/HQ/SolidDead.glb"],
    "foliage_material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_CardNeedle.mat",
    "trunk_material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_WetAgedWood.mat",
    "tree_count":1600,"forest_min":0.05,"forest_max":0.62,"max_slope_deg":34.0,
    "scale_min":6.0,"scale_max":11.0,"dead_ratio":0.06,"seed":201,
    "clear_primitive_forest":True,"y_offset":-0.3}, 500)
out.append("scatter="+json.dumps({k:res.get(k) for k in ("ok","placed","dead_placed")} if isinstance(res,dict) else {"r":str(res)[:60]}))
out.append("SAVE1="+str(save()))
Path("studio/autopilot/_rf.txt").write_text("\n".join(out), encoding="utf-8")
