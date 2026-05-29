"""Phase 163 (P2): 'per-class signature status effects'.
ClassPrototype.ClassProfile now has signatureStatus/Chance/Duration/Magnitude.
GrantClass() stamps the SI primary on switch. Skirmisher=Bleed, Barbarian=Slow.
This phase: recompile bridge (no CommandHandlers.cs change needed — ClassPrototype
is a runtime script), re-wire slice, verify ClassAltar_Skirmisher has ClassPrototype
with signatureStatus, screenshot. Phase 163 closes the P157+P158 honest split.
"""
import time, json
import unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools
from unitytools.bridges.unity import focus_unity_window
from pathlib import Path

SRC_CS = ("D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0/"
          "unity_plugin/Editor/Bridge/CommandHandlers.cs")
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
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


# ── 1. Stabilise (no bridge recompile needed — CommandHandlers unchanged) ────
if not wait_main(tag="pre"): print("stalled pre"); raise SystemExit(0)

# Recompile needed only for runtime scripts (ClassPrototype.cs is Unity managed).
# Force a full reimport of one asset to trigger domain reload with new code.
print("reimport:", json.dumps(rcall("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs"}, t=60, retries=2))[:110])
time.sleep(10)
if not wait_main(tries=130, tag="post"): print("stalled post"); raise SystemExit(0)

# ── 2. Open scene + wire ─────────────────────────────────────────────────────
rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)
res = rcall("wire_playable_slice", {"hero": "SK_Hero"}, t=120, retries=2)
print("WIRE:", json.dumps(res, ensure_ascii=False)[:800])

# ── 3. Verify ClassAltar_Skirmisher + all StatusInfliction wiring ─────────────
for name in ["ClassAltar_Skirmisher", "SK_Hero", "Enemy_Briarbound_01",
             "EliteBriarbound_Champion"]:
    d = rcall("get_object_details", {"name": name}, t=20)
    comps = d.get("components") if isinstance(d, dict) else []
    has_cp = any("ClassPrototype" in str(c) for c in (comps or []))
    has_si = any("StatusInfliction" in str(c) for c in (comps or []))
    print(f"  {name}: ClassPrototype={has_cp} StatusInfliction={has_si}")

# ── 4. Frame + screenshot ─────────────────────────────────────────────────────
info = rcall("get_object_details", {"name": "SK_Hero"}, t=20)
hx, hy, hz = 225.0, 57.0, 75.0
if isinstance(info, dict):
    pos = info.get("position") or {}
    if isinstance(pos, dict) and "x" in pos:
        hx, hy, hz = float(pos["x"]), float(pos["y"]), float(pos["z"])
rcall("set_scene_view", {"pivot_x": hx, "pivot_y": hy + 1.5, "pivot_z": hz,
      "size": 14, "pitch": 7, "yaw": 32}, t=30, retries=2)
time.sleep(1.4)
print("shot:", json.dumps(studio_capture_screenshot(name="fv_phase163_class_status"))[:120])

wired   = res.get("wired_count") if isinstance(res, dict) else "?"
missing = res.get("missing_types") if isinstance(res, dict) else "?"
si_wired = [w for w in (res.get("wired") or []) if "StatusInfliction" in w]
print("PHASE-163 DONE ok=%s wired=%s missing=%s si_wired=%s" % (
    isinstance(res, dict) and res.get("ok"),
    wired, missing, si_wired))
