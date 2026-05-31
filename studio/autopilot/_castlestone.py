import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_cs.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
# test fort'u sil
for _ in range(3): rc("delete_object", {"name":"FortTest"}, 10)
# yeni .mat import olsun
rc("execute_menu_item", {"path":"Assets/Refresh"}, 30); time.sleep(5); fresh()
# kaleye tas malzeme ata (govde). Cati ayri slot olabilir; once hepsine tas,
# sonra cati slot'una koyu malzeme istersek. Simdilik tas govde.
am = rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_CastleStone.mat",
    "name_contains":"GothicCastle","recurse":True}, 60)
out.append("mat="+json.dumps(am)[:140])
out.append("saved="+str(save()))
kp = pos_of("GothicCastle") or (-482,95,-311)
shot("castle_stone", kp[0]+50, kp[1]+28, kp[2]+50, 100, 8, 220)
Path("studio/autopilot/_cs.txt").write_text("\n".join(out), encoding="utf-8")
