"""Wait for Unity to be IDLE (ping responds fast), then run ONE clean
Briar Hollow blockout with generous timeouts. set_scale/position now
work (Phase 104 aliases). Self-paced, no hammering.
"""
import time, json
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from pathlib import Path

P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap(); U.connect(timeout=8.0)
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))

# Wait for IDLE: ping must return quickly several times in a row.
idle = 0
for attempt in range(40):
    t0 = time.time()
    try:
        U.call("ping", {}, timeout=8)
        dt = time.time() - t0
        if dt < 1.5:
            idle += 1
            if idle >= 3:
                print(f"Unity idle (ping {dt:.2f}s x{idle})"); break
        else:
            idle = 0
            print(f"  busy (ping {dt:.2f}s) attempt {attempt}")
    except Exception as e:
        idle = 0
        print(f"  busy/timeout attempt {attempt}: {str(e)[:60]}")
    time.sleep(6)
else:
    print("Unity stayed busy too long — likely a long asset import; retry later.")
    raise SystemExit(2)

def call(cmd, p, t=90):
    try: return U.call(cmd, p, timeout=t)
    except Exception as e: return {"ok": False, "error": str(e)[:150]}

print("open:", json.dumps(call("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}))[:120])
mp = call("make_terrain_playable", {"footprint_m": 1200, "relief_scale": 0.16,
          "character": "SK_Hero", "character_scale": 1.0})
print("MTP:", json.dumps(mp)[:280])
from unitytools.studio.tools import studio_realize_world, studio_capture_screenshot
rw = studio_realize_world(water_level=0.085, forest_count=240, relief_m=190.0)
print("REALIZE ok=", rw.get("ok"))

spawn = (mp.get("spawn") or "0,80,0").split(",")
sx, sy, sz = (float(spawn[0]), float(spawn[1]), float(spawn[2])) if len(spawn) == 3 else (0., 80., 0.)
def mk(name, dx, dz, prim, S, col):
    call("create_primitive", {"type": prim, "name": name,
         "position_x": sx+dx, "position_y": sy + S[1]*0.5 + 1, "position_z": sz+dz})
    call("set_scale", {"name": name, "x": S[0], "y": S[1], "z": S[2]})
    call("set_material_color", {"name": name, "r": col[0], "g": col[1], "b": col[2], "a": 1.0})
mk("Route_Spawn", 0, 0, "Cylinder", (4,0.4,4), (0.30,0.50,0.65))
mk("Camp_HearthRing", 16, 9, "Cylinder", (6,0.5,6), (0.20,0.14,0.10))
mk("Camp_Fire", 16, 9, "Cube", (1.8,2.4,1.8), (1.0,0.5,0.15))
for i in range(1,6):
    mk(f"Path_{i:02d}", i*8, 5+i*6, "Cube", (2,0.3,2), (0.32,0.30,0.27))
mk("Landmark_Spire", 56, 44, "Cylinder", (5,26,5), (0.22,0.20,0.24))
mk("Boss_ArenaRing", 84, 66, "Cylinder", (20,0.3,20), (0.16,0.12,0.10))
mk("Boss_Marker", 84, 66, "Cube", (3,5,3), (0.55,0.10,0.12))
# third-person cam near spawn looking at the route
call("set_camera_transform", {"name":"Main Camera","position_x":sx-26.0,"position_y":sy+18.0,"position_z":sz-30.0,"rotation_x":20.0,"rotation_y":40.0,"rotation_z":0.0})
call("save_scene", {})
print(json.dumps(studio_capture_screenshot(name="fv_briar_clean"))[:150])
print("BRIAR CLEAN DONE")
