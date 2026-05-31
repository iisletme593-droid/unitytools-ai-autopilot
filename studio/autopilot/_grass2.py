import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# yeni agac malzemesi + kale icin refresh
rc("execute_menu_item", {"path":"Assets/Refresh"}, 30); time.sleep(6); fresh()
# cim takviyesi: daha yogun, genis band
g=rc("scatter_terrain_grass", {"clump_count":6000,"band_min":0.03,"band_max":0.97,
     "max_slope_deg":42.0,"scale_min":3.5,"scale_max":8.0,"seed":113}, 150)
out.append("grass="+json.dumps({k:g.get(k) for k in ("placed",)} if isinstance(g,dict) else {}))
out.append("forest="+str(child_count("WorldForestGLB")))
out.append("campforest="+str(child_count("CampForest")))
out.append("saved="+str(save()))
Path("studio/autopilot/_grass2.txt").write_text("\n".join(out), encoding="utf-8")
