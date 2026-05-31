import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_terrpbr.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
G="Assets/FantasyRPG/Textures/Ground"
def layer(num, name, tile):
    return {"name":name,
            "diffuse":f"{G}/Ground{num}/Ground{num}_2K-JPG_Color.jpg",
            "normal": f"{G}/Ground{num}/Ground{num}_2K-JPG_NormalGL.jpg",
            "tile": tile}
# alttan uste: cim -> yosunlu orman -> kuru toprak -> cakil/tas
layers=[
    layer("054","Cayir", 14),
    layer("104","OrmanZemini", 16),
    layer("103","KuruToprak", 18),
    layer("037","Cakil", 12),
]
r = rc("apply_terrain_pbr_layers", {"layers":layers, "cutoffs":[0.30,0.58,0.82]}, 180)
out=["ok="+str(r.get("ok") if isinstance(r,dict) else r)]
if isinstance(r,dict):
    out.append("built="+json.dumps(r.get("built") or r)[:300])
    out.append("err="+str(r.get("error")))
out.append("saved="+str(save()))
Path("studio/autopilot/_terrpbr.txt").write_text("\n".join(out), encoding="utf-8")
