import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
# tum kok objeleri listele, oyuncu/karakter benzeri isimleri yakala
r = rc("list_root_objects", {}, 30) or {}
roots = r.get("roots") or []
out.append("ROOT_COUNT="+str(r.get("root_count")))
cand=[]
for o in roots:
    nm=str(o.get("name",""))
    low=nm.lower()
    if any(k in low for k in ["hero","player","warrior","knight","char","kahraman","nord","warden"]):
        cand.append(f"{nm} pos={o.get('pos')} rend={o.get('renderers')}")
out.append("CANDIDATES:")
out += cand if cand else ["(yok)"]
# tum kokleri da yaz (kisa)
out.append("ALL_ROOTS:")
out.append(", ".join(str(o.get("name","")) for o in roots))
Path("studio/autopilot/_findhero.txt").write_text("\n".join(out), encoding="utf-8")
