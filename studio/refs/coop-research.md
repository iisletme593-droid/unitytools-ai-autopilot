# Co-op fundamentals research (P2 502395b159da)

Genre mix lists **Knight Online (party/grind hooks)** — so co-op is a
long-term ambition. This note is the *fundamentals research* asked for
by the P2 task; it is grounded in the actual codebase, not generic.

## Finding: the codebase is hard single-local-player

Gameplay/ has **14 singletons** (`AudioManager`, `GameManager`,
`QuestSystem`, `LockOnSystem`, `CampProgression`, `BossEncounterManager`,
`WeatherSystem`, `VfxManager`, `DamageNumberSpawner`, `CutsceneController`,
`DialogueSystem`, `ScreenShake`, `ObjectPool`, `ProceduralWorldGenerator`)
and the pervasive pattern `GameObject.FindGameObjectWithTag("Player")`
(PlayerController, WarBanner, NightDanger, MusicDirector,
EncounterAmbience, CraftingStation, CampProgression, …). Every system
assumes **exactly one local player** and **one authority** (the local
process). There is no transform/state replication, no ownership model,
no tick/command separation.

## What real networked co-op would require

Player-as-list (not singleton tag lookup) · client/server authority on
combat + loot + camp progression · transform/animation/health
replication + interpolation · join/leave + spawn ownership · input
command routing. This is a deep, cross-cutting refactor of essentially
every system above — i.e. exactly the class of work DOCS marks
**"Kesinlikle Ertele"** (100-player / full MMO) and core-pillar #5
("token sonra — önce oyun hissi"). Building even a "networking slice"
now would either be a throwaway prototype or force that refactor early,
against the locked vertical-slice scope.

## Recommendation (scoped, honest — not a rubber-stamp)

1. **Defer the networking slice** for the vertical slice. Consistent
   with the existing producer decision *"Vertical slice scope lock"*
   and DOCS Kesinlikle Ertele. The slice stays single-player
   Souls-lite (Remnant 2 feel) on Briar Hollow.
2. **The concrete "temel/fundamentals" deliverable = identify the one
   cheap seam that de-risks future co-op without paying for it now:**
   the recurring `FindGameObjectWithTag("Player")` is the single
   chokepoint. A future additive `PlayerRegistry` (a static list of
   registered player roots — today it simply holds the one local
   player) would give every director one place to ask "who are the
   players?" instead of hard-coding the single lookup. Zero behaviour
   change today; turns a scattered cross-cutting assumption into one
   swappable point when/if co-op is greenlit. **Recommended but NOT
   built here** — building it now is scope creep on a research task;
   it belongs in its own backlog item if co-op is ever greenlit.

## Decision

Recorded via studio_propose_decision: *"Co-op deferred for vertical
slice; PlayerRegistry seam is the agreed fundamentals direction."*
