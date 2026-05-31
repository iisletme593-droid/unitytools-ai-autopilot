import sys, json; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect(); guard_scene()
lines=[]
lines.append("forest="+str(child_count("WorldForestGLB")))
lines.append("campforest="+str(child_count("CampForest")))
lines.append("worldgrass="+str(child_count("WorldGrass")))
cp=pos_of("GothicCastle"); lines.append("castle="+(f"{cp[0]:.0f},{cp[1]:.0f},{cp[2]:.0f}" if cp else "YOK"))
Path("studio/autopilot/_v2.txt").write_text("\n".join(lines), encoding="utf-8")
