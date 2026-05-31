import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene():
    Path("studio/autopilot/_wireout.txt").write_text("GUARD_FAIL", encoding="utf-8"); raise SystemExit
r = rc("wire_playable_slice", {"hero":"SK_Hero"}, 120)
out=[]
out.append("ok="+str(r.get("ok") if isinstance(r,dict) else r))
if isinstance(r,dict):
    out.append("wired_count="+str(len(r.get("wired") or [])))
    out.append("missing="+json.dumps(r.get("missing") or [])[:300])
    out.append("wired_sample="+json.dumps((r.get("wired") or [])[:12])[:400])
out.append("saved="+str(save()))
Path("studio/autopilot/_wireout.txt").write_text("\n".join(out), encoding="utf-8")
