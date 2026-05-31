import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene(): print("GUARD_FAIL"); sys.exit(1)
a = rc("analyze_lod_decimation_candidates", {}, 120) or {}
print("ANALYZE", json.dumps(a)[:600])
