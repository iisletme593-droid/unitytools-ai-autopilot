"""Synthesize the DOCS build-order + combat-state-spec into an
execution-ready P0 plan: write the studio sprint, and wire task
dependencies so /next yields build-order sequence. No recompile.
"""
import json, re
from pathlib import Path
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools

c, b, u = _bootstrap()
try: u.connect(timeout=3.0)
except Exception: pass
init_studio_unity(u); ut._UNITY = u
P = StudioPaths(project_root=Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0'))
[d.mkdir(parents=True, exist_ok=True) for d in P.all_dirs()]
init_studio_tools(StudioState(P))

from unitytools.studio.tools import (
    studio_write_sprint, studio_list_tasks, studio_add_task_dependency,
    studio_propose_decision)

tasks = studio_list_tasks().get("tasks", [])
def find(substr):
    for t in tasks:
        if substr.lower() in t["title"].lower():
            return t["id"]
    return None

SPRINT = """# Sprint — P0 Vertical Slice (DOCS build-order)

Source: DOCS/implementation/blueprint-build-order.md +
combat-state-spec.md. Execute IN ORDER; each stage gates the next.

## Stage 1 — Player Spine
PlayerCharacter + PlayerController + GameMode.
inherit template movement -> sprint -> stamina vars -> dodge input.

## Stage 2 — Combat Base
StaminaComponent + CombatComponent + WeaponProfile(StarterSword).
light attack -> heavy attack -> damage window -> hit-react event.
State machine (combat-state-spec): Idle/Move/Sprint/AttackLight/
AttackHeavy/Dodge/Block/HitReact/Recovery/Dead; phases Startup/
Active/Recovery/FinisherWindow. Rules: dodge costs stamina; low
stamina disables dodge+heavy; HitReact cancels attack; Dead locks
input; light=fast/low-cost/combo-open; heavy=slow/high-stagger/
clear hit-pause.

## Stage 3 — Enemy Base
Enemy_Base + BriarboundVillager + AIController_Base.
detect -> chase -> attack -> take damage -> death. Reads: sees ->
approaches -> telegraphs -> hits -> short opening after miss/block.

## Stage 4 — Loot & Inventory
LootPickup + Inventory + ItemDefinition.
pickup -> add to inventory -> single weapon slot.

## Stage 5 — Briar Hollow Slice
BriarHollow_Blockout + camp + 3 encounter points + mini-boss arena.
(Real-world terrain + biomes + forest + water already built via
studio_realize_world; needs make_terrain_playable rescale +
surface route — gated on one Unity recompile.)

## Stage 6 — Mini Boss
Boss_BarkMaiden: 3 attack patterns + short summon + arena zoning.

## Rule
Before any new asset: "is this really new, or a child of an
existing base class?" Early-stage: prefer child.
"""
print(json.dumps(studio_write_sprint(SPRINT))[:100])

# Wire build-order dependencies: representative P0 task per stage,
# later stage depends on earlier. /next will then surface Stage-1
# work first.
chain = [
    find("player controller setup"),
    find("stamina sistemi"),
    find("dodge"),
    find("light attack"),
    find("heavy attack"),
    find("basic enemy ai"),
    find("damage uygulama"),
    find("loot pickup"),
    find("inventory iskeleti"),
    find("Briar Hollow blockout"),
    find("first playable route"),
    find("mini boss arena"),
]
chain = [c for c in chain if c]
wired = 0
for earlier, later in zip(chain, chain[1:]):
    r = studio_add_task_dependency(later, earlier)  # later depends on earlier
    if isinstance(r, dict) and r.get("ok"):
        wired += 1
print(f"wired {wired} build-order dependencies across {len(chain)} P0 anchors")

print("decision:", studio_propose_decision(
    title="Execution follows DOCS blueprint-build-order",
    summary="P0 executes in 6 build-order stages; task deps wired so "
            "/next yields the correct sequence.",
    rationale="DOCS/implementation/blueprint-build-order.md: 'editor "
              "acildiginda dagilmadan ilerlemek'. Framework drives "
              "ordered execution.").get("decision_id"))
print("EXEC PLAN DONE")
