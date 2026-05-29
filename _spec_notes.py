"""Attach execution-ready engineering notes (synthesized from DOCS
implementation specs) to the Stage 1-2 P0 tasks /next yields first.
No recompile — pure framework/planning value.
"""
import json
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
from unitytools.studio.tools import studio_list_tasks, studio_append_task_note

tasks = studio_list_tasks().get("tasks", [])
def tid(sub):
    for t in tasks:
        if sub.lower() in t["title"].lower():
            return t["id"]
    return None

# (title-substring, synthesized engineering note)
NOTES = {
 "third-person template": (
  "STAGE 1 (build-order). Goal: third-person template opens clean, "
  "no errors. Assets: BP_TI_PlayerCharacter, BP_TI_PlayerController, "
  "BP_TI_GameMode. Acceptance: project boots to template map, WASD "
  "moves, camera follows. Ref: DOCS/implementation/blueprint-build-order.md #1."),
 "player controller setup": (
  "STAGE 1. Spring-arm + camera lag + camera collision on "
  "BP_TI_PlayerCharacter. Inherit template movement; add sprint "
  "(LeftShift, drains 14 stamina/s). Camera: lag enabled, probe "
  "collision so it never clips terrain. Acceptance: smooth follow, "
  "no wall clip, sprint visibly faster. Ref: build-order #1, "
  "input-combo-layout.md (LeftShift=sprint)."),
 "input mapping": (
  "STAGE 1. Key map (input-combo-layout.md): LMB light, "
  "MouseWheelDown heavy, RMB block, Space dodge, LeftShift sprint, "
  "Q/R skills, F battlecry, C finisher, X weapon-swap, V two-hand, "
  "E interact, MiddleMouse lock-on, Tab inventory, 1-4 quickslots. "
  "Acceptance: every action bound + logs on press."),
 "stamina sistemi": (
  "STAGE 2. BPC_TI_StaminaComponent (combat-data-defaults.md): "
  "Max=100, Regen=18/s, SprintDrain=14/s, DodgeCost=24, "
  "HeavyCost=32, BlockDrainPerHit=18, ExhaustedRecoveryDelay=1.15. "
  "Rule: stamina<cost disables dodge & heavy. Acceptance: bar "
  "drains/regens per values; exhausted state gates actions."),
 "dodge": (
  "STAGE 2. Space. DodgeCost=24 stamina; "
  "DodgeInvulnerabilityWindow=0.32; DodgeCounterWindow=0.42; "
  "DodgeRecoveryTime=0.28. Dodge moves camera-relative; short "
  "recovery prevents spam; disabled if stamina<24. Combo: "
  "Space->LMB = Sidestep Reaver (within DodgeCounterWindow). "
  "Ref: combat-state-spec.md, combat-data-defaults.md."),
 "light attack": (
  "STAGE 2. LMB. LightAttackStaminaCost=12, AttackStartupTime=0.16, "
  "AttackRange=220, ComboResetWindow=1.1, ComboBranchWindow=0.34, "
  "AttackRecoveryTime=0.36, RecoveryExitWindow=0.24. Combo: "
  "LMB,LMB,LMB = Cleaver Chain (fast, low commit, grind spine). "
  "Phases: Startup->Active->Recovery. HitReact cancels it."),
 "heavy attack": (
  "STAGE 2. MouseWheelDown. HeavyAttackStaminaCost=30, slower "
  "startup, higher stagger, clear HitPauseTime=0.06, "
  "StaggerThreshold=40. Combo: LMB,LMB,MWD = Rend Breaker "
  "(shield/posture opener); MWD,LMB = Crush Followup. Risky, "
  "decisive. Ref: combat-state-spec.md, combat-data-defaults.md."),
 "hit reaction": (
  "STAGE 2. HitReactDuration=0.45, HitPauseTime=0.06. HitReact "
  "cancels any active attack. Hit-pause = brief freeze for impact "
  "weight (core pillar 1: combat tok). Anim+camera+audio same dir."),
 "death state": (
  "STAGE 2/3. 'Dead' state locks ALL input; DeathCleanupDelay=8.0 "
  "before cleanup. Applies to player + enemies. Ref: combat-state-spec.md."),
 "damage uygulama": (
  "STAGE 2. AttackRange=220, CounterDamageMultiplier=1.18, "
  "TwoHandDamageMultiplier=1.22, CampBuffDamageBonus=1.08. Damage "
  "applied during Active phase only. Punish: enemy whiff -> "
  "MissRecoveryDuration=0.68 opening, PunishWindowDuration=0.72."),
 "basic enemy ai": (
  "STAGE 3. BP_TI_Enemy_Base, BP_TI_Enemy_BriarboundVillager, "
  "BP_TI_AIController_Base. Read: sees -> approaches -> telegraph "
  "(TelegraphTime=0.42) -> hits -> short opening after miss/block. "
  "Chain: detect->chase->attack->take damage->death. Fair but hard."),
 "enemy ai patrol": (
  "STAGE 3. Patrol->Detect->Chase->Attack->Return state chain on "
  "AIController. Return-to-post if target lost. Telegraph 0.42 so "
  "attacks are readable. Ref: build-order #3, combat-state-spec.md."),
}

applied = 0
for sub, note in NOTES.items():
    i = tid(sub)
    if not i:
        print("  (no task for)", sub); continue
    r = studio_append_task_note(i, note)
    if isinstance(r, dict) and r.get("ok"):
        applied += 1
        print("noted:", sub[:34])
print(f"attached {applied} execution-ready spec notes")
print("SPEC NOTES DONE")
