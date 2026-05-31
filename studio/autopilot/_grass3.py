import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
out.append("campforest_once="+str(child_count("CampForest")))
g=rc("scatter_terrain_grass", {"clump_count":6000,"band_min":0.03,"band_max":0.97,
     "max_slope_deg":42.0,"scale_min":3.5,"scale_max":8.0,"seed":113}, 150)
out.append("grass="+json.dumps(g)[:120] if isinstance(g,dict) else "grass=FAIL")
out.append("worldgrass_sonra="+str(child_count("WorldGrass")))
out.append("saved="+str(save()))
Path("studio/autopilot/_g3.txt").write_text("\n".join(out), encoding="utf-8")
