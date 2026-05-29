# Sprint — P0 Vertical Slice (DOCS build-order)

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
