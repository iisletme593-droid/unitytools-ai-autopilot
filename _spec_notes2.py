"""Complete P0 execution-readiness: attach DOCS-synthesized notes to
the remaining P0 tasks (Stage 4-6 + UI/equipment/loadout/world).
Sources: weapon-loadout-structure.md, level-instance-links.md,
blueprint-build-order.md #5-6, combat-data-defaults.md. No recompile.
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

NOTES = {
 "loot pickup": (
  "STAGE 4. BP_TI_LootPickup + ST_TI_ItemDefinition. Pickup on E "
  "(InteractionRange=220). Scene loot (level-instance-links.md): "
  "LootChest_Bridge LootTier=2; OfferingPickup_North/Bridge/Shrine "
  "OfferingValue=1 each. Acceptance: E picks up -> item enters "
  "inventory -> world actor removed. Ref: build-order #4."),
 "inventory iskeleti": (
  "STAGE 4. WBP_TI_Inventory + ST_TI_ItemDefinition. Minimal: add "
  "item, single weapon slot, Tab opens panel. Not full grid yet. "
  "Acceptance: picked loot shows in list; weapon slot equips. "
  "Ref: build-order #4."),
 "basic equipment": (
  "STAGE 4. ST_TI_ItemDefinition + weapon-loadout-structure.md "
  "common fields: WeaponTag, EquipmentTier, WeaponDamage, "
  "PostureDamage, AttackReach, AttackSpeedModifier, bSupportsBlock, "
  "bSupportsTwoHandMode, bStartsUnlocked. Player state: "
  "PrimaryWeaponTag, CurrentWeaponProfileTag, CurrentLoadoutTier."),
 "class loadout rack": (
  "STAGE 4/5. weapon-loadout-structure.md. Actors: "
  "BP_TI_Weapon_BarbarAxe/BarbarGreatsword/WardenShield, "
  "BP_TI_WeaponRack(TI_Interact/TI_GrantLoadout/TI_UpdateVisualTier), "
  "BP_TI_ArmorStand(TI_GrantArmorTier), BP_TI_WarBanner"
  "(TI_GrantCampBuff). Player graph: TI_HandleWeaponSwap(X), "
  "TI_HandleTwoHandToggle(V), TI_RefreshCombatProfile. Camp "
  "placements: WeaponRack_BarbarCamp/GreatswordCamp/ShieldCamp, "
  "ArmorStand_Camp, WarBanner_Camp. Weapon diff felt in combat, "
  "not just name."),
 "health/stamina UI": (
  "STAGE 4. HUD: health bar + stamina bar (StaminaComponent Max=100) "
  "+ guard meter (BlockStability=55, GuardRegen=22/s). Stamina bar "
  "must visibly drain on sprint/dodge/heavy and gate actions when "
  "<cost. Ref: combat-data-defaults.md."),
 "skill bar": (
  "STAGE 4. Skill bar (Q/R/F/C) + quest tracker shell + mini-map "
  "shell. Just shells/placeholders for the slice. Q primary, R "
  "secondary, F battlecry, C finisher (FinisherConfirmWindow=1.1). "
  "Ref: input-combo-layout.md."),
 "Briar Hollow blockout": (
  "STAGE 5. LVL_TI_BriarHollow_Blockout. Real terrain+biomes+"
  "forest+water already built (studio_realize_world). Layout "
  "(level-instance-links.md): CampAnchor_Main, EncounterMarker_"
  "North/Bridge/Shrine, SoulShrine_OldRoots, BossGate_RootVeil, "
  "BossArena_BarkMaiden, PatrolAnchors, RestTotem_Bridge(8s)/"
  "Shrine(12s), CraftingBench_Camp(tier1), LootChest_Bridge(tier2). "
  "GATED: needs make_terrain_playable recompile for human-scale "
  "surface placement of these anchors."),
 "first playable route": (
  "STAGE 5. EncounterDirector_BriarHollow: CurrentRoutePhase=Camp, "
  "EncounterProgressCount=0, RequiredBossUnlockCount=3. Loop: "
  "spawn->Camp->collect 3 Offerings (North/Bridge/Shrine, value 1 "
  "each)->offer at SoulShrine_OldRoots (RequiredOfferingCount=3)->"
  "BossGate_RootVeil opens->BarkMaiden. This IS the vertical-slice "
  "spine (Valheim explore + KO grind + Remnant boss)."),
 "world partition": (
  "STAGE 5. Zone the slice into streaming regions: Camp / North / "
  "Bridge / Shrine / BossArena. Keep only the active region + "
  "neighbors loaded. Vertical slice = one cell set, no full open "
  "world. Defer true large-scale streaming (DOCS Kesinlikle Ertele)."),
 "mini boss arena": (
  "STAGE 6. BP_TI_Boss_BarkMaiden in BossArena_BarkMaiden. "
  "BossSpawn_BarkMaiden EnemyStateTag=Dormant -> activates when "
  "BossGate opens. 3 attack patterns + short summon + arena zoning "
  "(lane closure). Reads via combat-state-spec telegraph(0.42)->"
  "impact->opening. Ref: build-order #6, level-instance-links.md."),
}

applied = 0
for sub, note in NOTES.items():
    i = tid(sub)
    if not i:
        print("  (no task)", sub); continue
    r = studio_append_task_note(i, note)
    if isinstance(r, dict) and r.get("ok"):
        applied += 1; print("noted:", sub[:32])
print(f"attached {applied} more spec notes; P0 backlog execution-ready")
print("SPEC NOTES 2 DONE")
