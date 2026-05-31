import sys, json, time; from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent)); from ap import *
connect()
# compile state
es = rc("get_editor_state", {}, 20) or {}
print("COMPILE", json.dumps(es))
guard_scene()
s = rc("list_scenes", {}, 15) or {}
print("SCENE", s.get("active_scene"))
# inventory of everything we built
groups = ["WorldForestGLB","WoodHouse","GothicCastle","CampSite","CampDressing",
          "CampWarmth","RoadDressing","FernUndergrowth","RockScatter",
          "MonsterSpawns","PathRoute","PlayerSpawn","RumorBoard","LightBeam"]
ok = True
for nm in groups:
    d = rc("get_object_details", {"name": nm}, 12) or {}
    if d.get("name"):
        print(f"  {nm}: children={d.get('child_count')}")
    else:
        print(f"  {nm}: MISSING"); ok = False
# scripts present on disk
import os
SD = "C:/Users/Kitli Matmazel/CascadeProjects/windsurf-project/UnityProject/Assets/FantasyRPG/Scripts/UI/Gameplay"
for cs in ["CharacterSelectScreen.cs","CampfireRest.cs","RumorBoard.cs","StarterLoadout.cs","Progression.cs","PauseMenu.cs"]:
    print(f"  SCRIPT {cs}: {'OK' if os.path.exists(SD+'/'+cs) else 'MISSING'}")
print("ALL_OK", ok)
print("SAVE", save())
