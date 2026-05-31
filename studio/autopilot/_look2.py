import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
# verify dressing group exists with children + list a couple positions
d = rc("get_object_details", {"name":"CampDressing"}, 15) or {}
print("CampDressing children:", d.get("child_count"))
for nm in ["WeaponRack","WarBanner","CraftBench","Table1"]:
    p = pos_of(nm)
    print(f"  {nm}: {'('+','.join(f'{v:.0f}' for v in p)+')' if p else 'MISSING'}")
