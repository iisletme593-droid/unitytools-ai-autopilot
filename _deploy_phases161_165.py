"""Unified deploy runner for Phases 161-165.
Recompiles the bridge (CommandHandlers.cs has all Phase 161-165 wiring),
re-wires the slice, verifies all new components, screenshots.

Phase 161: StatusInfliction + combat hit hookup
Phase 162: PlayerRegistry 8-callsite migration
Phase 163: Per-class signature status effects (ClassPrototype)
Phase 164: RestTotem respawn anchor + heal-rest
Phase 165: Offering → SoulShrine → BossGate spine

Plus: RpgHudController got status/offering/lore HUD hooks (Phase 166, no wire needed).
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


# ── 1. Stabilise + recompile bridge ─────────────────────────────────────────
if not wait_main(tag="pre"): print("stalled pre"); raise SystemExit(0)
print("recompile:", json.dumps(rcall("import_asset", {
    "src_path": SRC_CS,
    "dst_relative": "Editor/UnityToolsBridge/CommandHandlers.cs"}, t=60, retries=2))[:110])
time.sleep(10)
if not wait_main(tries=130, tag="post"): print("stalled post"); raise SystemExit(0)

# ── 2. Open scene + wire slice (all phases) ──────────────────────────────────
rcall("open_scene", {"path": "Assets/Scenes/ForgottenValley_VS.unity"}, t=120)
res = rcall("wire_playable_slice", {"hero": "SK_Hero"}, t=120, retries=2)
print("WIRE:", json.dumps(res, ensure_ascii=False)[:1200])

# ── 3. Verify all Phase 161-165 objects ─────────────────────────────────────
verify = {
    # Phase 161: StatusInfliction
    "SK_Hero": ["StatusInfliction", "StatusEffectComponent"],
    "Enemy_Briarbound_01": ["StatusInfliction", "StatusEffectComponent", "EliteAffix"],
    "EliteBriarbound_Champion": ["StatusInfliction", "StatusEffectComponent", "EliteAffix"],
    # Phase 163: ClassPrototype (Skirmisher)
    "ClassAltar_Skirmisher": ["ClassPrototype"],
    # Phase 164: RestTotem
    "RestTotem_Camp": ["RestTotem"],
    "RestTotem_Bridge": ["RestTotem"],
    # Phase 165: Offering spine
    "OfferingPickup_North": ["LootPickup"],
    "OfferingPickup_Bridge": ["LootPickup"],
    "OfferingPickup_Shrine": ["LootPickup"],
    "SoulShrine_OldRoots": ["SoulShrine"],
    "BossGate_RootVeil": ["BossGate"],
}
for name, expected in verify.items():
    d = rcall("get_object_details", {"name": name}, t=20)
    comps = d.get("components") if isinstance(d, dict) else []
    comp_str = ", ".join(str(c) for c in (comps or []))
    missing_c = [e for e in expected if e not in comp_str]
    status = "OK" if not missing_c else f"MISSING={missing_c}"
    print(f"  {name}: {status}")

# ── 4. Screenshot ─────────────────────────────────────────────────────────────
info = rcall("get_object_details", {"name": "SK_Hero"}, t=20)
hx, hy, hz = 225.0, 57.0, 75.0
if isinstance(info, dict):
    pos = info.get("position") or {}
    if isinstance(pos, dict) and "x" in pos:
        hx, hy, hz = float(pos["x"]), float(pos["y"]), float(pos["z"])
rcall("set_scene_view", {"pivot_x": hx + 12, "pivot_y": hy + 4, "pivot_z": hz + 12,
      "size": 24, "pitch": 12, "yaw": 22}, t=30, retries=2)
time.sleep(1.4)
print("shot:", json.dumps(studio_capture_screenshot(name="fv_phases161_165_unified"))[:120])

wired   = res.get("wired_count") if isinstance(res, dict) else "?"
missing = res.get("missing_types") if isinstance(res, dict) else "?"
si_wired     = [w for w in (res.get("wired") or []) if "StatusInfliction" in w]
totem_wired  = [w for w in (res.get("wired") or []) if "RestTotem" in w]
offer_wired  = [w for w in (res.get("wired") or []) if "offering" in w.lower()]
print("PHASES 161-165 DONE ok=%s wired=%s missing=%s si=%d totems=%d offerings=%d" % (
    isinstance(res, dict) and res.get("ok"),
    wired, missing, len(si_wired), len(totem_wired), len(offer_wired)))
