import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
out=[]
out.append("EncounterMarkers="+str(child_count("EncounterMarkers")))
for nm in ["NorthAmbush","RotfangRun","ShrinePressure","DungeonGate_OldShrine"]:
    out.append(f"{nm}={'OK' if pos_of(nm) else 'MISSING'}")
out.append("forest="+str(child_count("WorldForestGLB")))
s=rc("list_scenes",{},15) or {}; out.append("scene="+str(s.get("active_scene")))
Path("studio/autopilot/_enc_chk.txt").write_text(" | ".join(out), encoding="utf-8")
