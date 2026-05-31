import sys, json, math, random; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_ftc.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
rng=random.Random(77)
out=[]

# yapilar (ustlerine agac koymayacagiz)
structs=[]
for nm in ["Campfire","WoodHouse","GothicCastle","CampSite","RumorBoard","CraftStation"]:
    p=pos_of(nm)
    if p: structs.append((p[0],p[2], 14 if "Castle" in nm else 8))  # (x,z,bos_yaricap)

cf=pos_of("Campfire") or (-526,141,-98)
def clash(x,z):
    for sx,sz,rad in structs:
        if math.hypot(x-sx,z-sz)<rad: return True
    return False

# eski grubu temizle
for _ in range(2): rc("delete_object", {"name":"CampForest"}, 10)
rc("create_empty", {"name":"CampForest","position":{"x":cf[0],"y":cf[1],"z":cf[2]}}, 12)

CARD="Assets/Art/HQ/CardFir.glb"
DEAD="Assets/Art/HQ/SolidDead.glb"
MAT_F="Assets/FantasyRPG/Generated/Materials/HDRP_M_CardNeedle.mat"
MAT_T="Assets/FantasyRPG/Generated/Materials/HDRP_M_WetAgedWood.mat"

n=0; tries=0
# kamp+ev merkezli 18-95m halkada agac
center=((cf[0]+(-510))/2, (cf[2]+(-88))/2)
while n<70 and tries<400:
    tries+=1
    a=rng.uniform(0,math.tau); rad=rng.uniform(16,95)
    x=center[0]+math.cos(a)*rad; z=center[1]+math.sin(a)*rad
    if clash(x,z): continue
    asset = DEAD if rng.random()<0.08 else CARD
    nm=f"CampTree_{n:03d}"
    r=place_pinned(asset, x, z, rng.uniform(2.0,3.6), nm, parent="CampForest",
                   glb=True, rot_y=rng.uniform(0,360), y_offset=-0.2,
                   min_surface_y=5.0, max_slope_deg=38.0)
    if r:
        # foliage malzeme (CardFir 2 slot: 0 govde 1 igne)
        rc("assign_material_asset", {"material_path":MAT_F,"name_contains":nm,"recurse":True}, 20)
        n+=1
out.append(f"agac yerlesti: {n} ({tries} deneme)")
out.append(f"CampForest child: {child_count('CampForest')}")

# cimen: kamp bolgesine yogun (scatter_terrain_grass ayri grup, agaclari bozmaz)
g=rc("scatter_terrain_grass", {"clump_count":3000,"band_min":0.04,"band_max":0.95,
     "max_slope_deg":40.0,"scale_min":3.0,"scale_max":7.0,"seed":91}, 120)
out.append("grass="+json.dumps({k:g.get(k) for k in ("placed",)} if isinstance(g,dict) else {}))
out.append("forest_intact="+str(child_count("WorldForestGLB")))
out.append("saved="+str(save()))
Path("studio/autopilot/_ftc.txt").write_text("\n".join(out), encoding="utf-8")
