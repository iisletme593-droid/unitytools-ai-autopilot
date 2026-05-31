import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
import json
names=sys.argv[1].split(",") if len(sys.argv)>1 else []
for nm in names:
    d=rc("get_object_details",{"name":nm},15) or {}
    print(f"{nm}: {'children='+str(d.get('child_count')) if d.get('name') else 'MISSING'}")
