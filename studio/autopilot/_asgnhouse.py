import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
am = rc("assign_material_asset", {"material_path":"Assets/FantasyRPG/Generated/Materials/HDRP_M_WoodHouse.mat",
    "name_contains":"WoodHouse","recurse":True}, 60)
save()
mp = rc("get_material_properties", {"name":"WoodHouse"}, 20) or {}
Path("studio/autopilot/_ah.txt").write_text(
    json.dumps({"assign_ok":am.get("ok") if isinstance(am,dict) else am,
                "renderers":am.get("assigned_renderers") if isinstance(am,dict) else None,
                "now_mat":mp.get("material"),"shader":mp.get("shader")}), encoding="utf-8")
