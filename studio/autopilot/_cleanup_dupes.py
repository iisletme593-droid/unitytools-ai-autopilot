import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_dupes.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
out=[]
# acikca artik olanlari sil
for nm in ["BossArena_old","MonsterSpawns_old","FernUndergrowth_old","Camp_extra"]:
    r = rc("delete_object", {"name": nm}, 12)
    out.append(f"{nm}: {'silindi' if isinstance(r,dict) and r.get('ok') else 'yok/atlandi'}")
# WorldWater 2x -> birini sil (delete tek eslesme siler; ikinci kalir)
r = rc("delete_object", {"name": "WorldWater"}, 12)
out.append("WorldWater(1): " + ("silindi" if isinstance(r,dict) and r.get("ok") else "yok"))
# kalan kok sayisi
rr = rc("list_root_objects", {}, 30) or {}
out.append("ROOT_COUNT_simdi=" + str(rr.get("root_count")))
ww = [o for o in (rr.get("roots") or []) if str(o.get("name",""))=="WorldWater"]
out.append("WorldWater_kalan=" + str(len(ww)))
out.append("forest=" + str(child_count("WorldForestGLB")))
out.append("saved=" + str(save()))
Path("studio/autopilot/_dupes.txt").write_text("\n".join(out), encoding="utf-8")
