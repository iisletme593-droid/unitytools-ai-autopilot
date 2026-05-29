"""Phase 165 (P3): 'Offering → SoulShrine → BossGate spine'.
OfferingTracker + SoulShrine + BossGate + LootPickup hook.
The actual gameplay loop: collect 3 offerings -> SoulShrine ritual -> boss gate opens.
"""
import time, json
import unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
P = StudioPaths(project_root=Path('.'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
c, b, U = _bootstrap()
init_studio_unity(U); ut._UNITY = U
init_studio_tools(StudioState(P))
from unitytools.studio.tools import studio_capture_screenshot


def fresh(t=8.0):
    try: U.disconnect()
    except Exception: pass
    try: return U.connect(timeout=t)
    except Exception: return False


def rcall(cmd, p, t=120, retries=3):
    for k in range(retries):
        try:
            return U.call(cmd, p, timeout=t)
        except Exception as e:
            print(f"  {cmd} fail#{k}: {str(e)[:50]}")
            focus_unity_window(); fresh(); time.sleep(3)
    return {"ok": False, "error": f"{cmd} x{retries}"}


def wait_main(tries=130, gap=7, tag="m"):
    ok = 0
    for i in range(tries):
        if i % 3 == 0: focus_unity_window()
        fresh()
        t0 = time.time()
        try:
            r = U.call("list_root_objects", {}, timeout=22)
            if isinstance(r, dict) and r.get("ok") and time.time()-t0 < 6.0:
                ok += 1
                if ok >= 2: return True
            else: ok = 0
        except Exception as e:
            ok = 0; print(f"[{tag}] busy#{i}: {str(e)[:42]}")
        time.sleep(gap)
    return False


if not wait_main(tag="pre"): print("stalled pre"); raise SystemExit(0)
print("recompile:", json.dumps(rcall("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs"}, t=60, retries=2))[:110])
time.sleep(10)
if not wait_main(tries=130, tag="post"): print("stalled post"); raise SystemExit(0)

rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)
res = rcall("wire_playable_slice", {"hero": "SK_Hero"}, t=120, retries=2)
print("WIRE:", json.dumps(res, ensure_ascii=False)[:900])

# Verify spine objects
spine = ["OfferingPickup_North", "OfferingPickup_Bridge", "OfferingPickup_Shrine",
         "SoulShrine_OldRoots", "BossGate_RootVeil",
         "RestTotem_Camp", "RestTotem_Bridge"]
for name in spine:
    d = rcall("get_object_details", {"name": name}, t=20)
    comps = d.get("components") if isinstance(d, dict) else []
    comp_names = ", ".join(str(c) for c in (comps or []))[:80]
    print(f"  {name}: {comp_names}")

missing = res.get("missing_types") if isinstance(res, dict) else "?"
offering_wired = [w for w in (res.get("wired") or []) if "offering" in w.lower() or "OfferingPickup" in w]
print(f"  missing={missing}  offering_wired={offering_wired}")

# Frame spine area for screenshot
info = rcall("get_object_details", {"name": "SK_Hero"}, t=20)
hx, hy, hz = 225.0, 57.0, 75.0
if isinstance(info, dict):
    pos = info.get("position") or {}
    if isinstance(pos, dict) and "x" in pos:
        hx, hy, hz = float(pos["x"]), float(pos["y"]), float(pos["z"])
rcall("set_scene_view", {"pivot_x": hx + 10, "pivot_y": hy + 3, "pivot_z": hz + 10,
      "size": 22, "pitch": 10, "yaw": 25}, t=30, retries=2)
time.sleep(1.4)
print("shot:", json.dumps(studio_capture_screenshot(name="fv_phase165_offering_spine"))[:120])
print("PHASE-165 DONE ok=%s wired=%s missing=%s" % (
    isinstance(res, dict) and res.get("ok"),
    res.get("wired_count") if isinstance(res, dict) else "?",
    missing))
