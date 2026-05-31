import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
if not guard_scene(): print("GUARD_FAIL"); sys.exit(1)
d = rc("diagnose_material_issues", {}, 60) or {}
print("DIAG", json.dumps({k:d.get(k) for k in ("renderers","missing_materials","broken_materials","materials_with_textures","pipeline")}))
if (d.get("missing_materials",0) or d.get("broken_materials",0)):
    r = rc("repair_material_issues", {}, 120) or {}
    print("REPAIR", json.dumps({k:r.get(k) for k in ("repaired_materials","created_materials","scanned_renderers")}))
else:
    print("REPAIR skipped (0 broken/missing)")
# also repair texture import settings if available
try:
    t = rc("repair_texture_import_settings", {}, 90) or {}
    print("TEXFIX", json.dumps(t)[:120])
except Exception as e:
    print("TEXFIX n/a")
print("SAVE", save())
print("JOB_DONE hdrp mats")
