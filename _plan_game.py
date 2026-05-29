"""One-shot studio planner for the 4-pillar mashup.
Valheim + V Rising + Knight Online + Remnant 2 -> 'Forgotten Valley'.
Writes GDD / Art Bible / Audio Brief, milestone + task backlog, decisions.
"""
import json
from pathlib import Path
import unitytools.tools, unitytools.tools.unity_tools as ut
from unitytools.cli.entry import _bootstrap
from unitytools.studio import init_studio_unity, StudioPaths, StudioState, init_studio_tools

config, blender, unity = _bootstrap()
unity.connect(timeout=3.0)
init_studio_unity(unity); ut._UNITY = unity

proj = Path('D:/UnityToolsV2/.claude/worktrees/wizardly-williams-9493d0')
paths = StudioPaths(project_root=proj)
[d.mkdir(parents=True, exist_ok=True) for d in paths.all_dirs()]
init_studio_tools(StudioState(paths))

from unitytools.studio.tools import (
    studio_write_gdd, studio_write_art_bible, studio_write_audio_brief,
    studio_add_milestone, studio_add_task, studio_propose_decision,
)

GDD = """# Forgotten Valley - Game Design Document

## One-line
A 2-hour, immersive single-player survival-explore loop: wander a moody
realistic valley, gather, raise a small home base, survive the night,
beat a mini-boss, glimpse the next biome. Relaxing spine, real teeth.

## The 4-pillar mix (best parts only)
- **Valheim**  -> the SPINE: chill open exploration, gathering, light
  base building, biome curiosity, stamina-paced physical combat,
  cosy-but-dangerous tone.
- **V Rising**  -> the RHYTHM: a day/night threat cycle. Day = explore,
  gather, build, relax. Night = the valley turns hostile; a power
  progression (relic shards) gates how deep you can push.
- **Remnant 2** -> the COMBAT: responsive third-person ranged+melee
  with a dodge-roll, readable enemy tells, one hand-crafted mini-boss.
  Tuned FORGIVING (this is a kafa-dagitma game, not a soulslike grind).
- **Knight Online** -> the HOOKS: satisfying loot drops + a couple of
  visible session goals (fill the relic meter, upgrade the hearth) so
  2 hours has a clear arc and a payoff.

## Core loop (a single 2h session)
explore valley -> gather wood/stone/herb/relic-shard -> upgrade hearth
(unlocks: torch radius, stamina, a weapon tier) -> survive night wave
at the hearth -> track + beat the Grove Warden mini-boss -> open the
sealed pass (teaser of biome 2) -> session ends on a high.

## Vertical slice scope (what we build FIRST)
ONE valley biome, realistic URP forest, third-person controller with
dodge, 3 gather resources, a 3-tier hearth, ONE night wave, ONE
mini-boss (Grove Warden), the sealed-pass teaser. Everything else
(extra biomes, castle building, co-op, nations/PvP) is POST-slice.

## Non-goals for the slice
No multiplayer. No procedural generation yet (hand-built valley first).
No inventory Tetris. No skill tree screen (progression = hearth tiers).

## Session feel target
First 20 min: calm, curious, "nereye gitsem". Mid: light tension as
relic meter rises. Night: a real but beatable spike. End: mini-boss
catharsis + a door cracking open to "next time".
"""

ARTB = """# Forgotten Valley - Art Bible

## Render target
Unity URP. Goal = 'grounded realistic', NOT photoreal HDRP. A weak GPU
must hold 60fps at 1080p. Stylized-realistic: real proportions + PBR
materials, but readable silhouettes and a controlled palette.

## Mood
Overcast Nordic-temperate valley. Damp. Low sun. Volumetric-ish fog
but BOUNDED (you can always see ~40-60m; the moody-fog mistake earlier
was unbounded fog -> flat void). Fog is atmosphere, never a wall.

## Palette
Desaturated greens/greys, wet bark browns, cold blue shadow, one warm
accent = the hearth fire + relic shards (amber/orange) so the player's
eye always finds 'home' and 'goal'.

## Lighting
Single soft directional 'sun' low on the horizon (golden-hour-ish),
gentle ambient from sky, baked where static. Night = moonlight (cool,
low) + hearth as the only warm pool. Contrast between safe-warm and
wild-cold is the whole visual thesis.

## Performance rails (URP)
- Tris budget on screen: <= ~900k. LODs on every tree/rock.
- Realtime lights: sun + hearth + max 4 small point lights at night.
- Fog: linear, start ~15m end ~70m. NEVER exponential-squared at high
  density (that was the void bug).
- One post-process volume: subtle tonemap (ACES), gentle vignette,
  mild bloom on the hearth/relics only.

## Readability rules
Interactables get a faint rim/emissive. Enemies silhouette dark
against fog. The hearth glow is visible from anywhere in the valley.
"""

AUDIO = """# Forgotten Valley - Audio Brief

## Pillars
- Ambient bed: wind in pines, distant water, sparse bird/creak. Calm
  by day; the bed thins + a low drone enters as night approaches
  (the V-Rising 'rhythm' cue, audio-first).
- Hearth: warm crackle loop, louder as you get close = audible 'home'.
- Combat: weighty but not harsh hits; a clear enemy 'tell' sound so
  the forgiving dodge window is learnable.
- Mini-boss: a leitmotif that fades the ambient bed entirely.
- Loot: a short bright chime on drop (the Knight-Online dopamine hook).

## Mix priority
Footsteps + enemy tells > ambient > music. The player must always
hear danger over atmosphere.
"""

print(json.dumps(studio_write_gdd(GDD), indent=1)[:200])
print(json.dumps(studio_write_art_bible(ARTB), indent=1)[:200])
print(json.dumps(studio_write_audio_brief(AUDIO), indent=1)[:200])

ms = studio_add_milestone(
    name="Vertical Slice - Forgotten Valley",
    description="One realistic valley biome with the full explore->gather"
                "->upgrade->night->mini-boss loop, 60fps on weak GPU.",
)
mid = ms.get("milestone_id", "")
print("milestone:", ms)

TASKS = [
    ("level_designer", "Build clean ForgottenValley_VS scene: terrain bowl, hero path, hearth clearing, sealed pass", "Hand-built valley, no autopilot junk. Readable landmarks."),
    ("tech_artist", "URP realistic baseline: low golden sun, ACES tonemap volume, BOUNDED linear fog 15-70m", "Fix the unbounded-fog void mistake. Lock perf rails."),
    ("tech_artist", "LOD + tris budget pass: every tree/rock LOD group, on-screen <=900k", "Weak-GPU 60fps gate."),
    ("designer", "Third-person controller: move, sprint(stamina), dodge-roll, interact", "Remnant-feel but forgiving dodge window."),
    ("designer", "Gather system: wood/stone/herb/relic-shard nodes + pickup", "Valheim spine."),
    ("designer", "Hearth 3-tier upgrade: torch radius / stamina / weapon tier", "Progression without a skill screen."),
    ("designer", "Day/night cycle + relic meter drives night threat level", "V-Rising rhythm."),
    ("designer", "Night wave at hearth: forgiving but real spike", "The tension beat."),
    ("designer", "Grove Warden mini-boss: 2 tells, 1 catharsis kill", "Remnant boss, tuned kind."),
    ("art_director", "Hearth + relic amber accent pass; interactable rim cue", "Eye always finds home + goal."),
    ("qa", "60fps weak-GPU check + fog-never-a-wall visual regression", "Guard the two known failure modes."),
    ("producer", "Session arc tuning: 20min calm / mid tension / night spike / boss payoff", "2h kafa-dagitma feel."),
]
for role, title, desc in TASKS:
    r = studio_add_task(title=title, role=role, description=desc, milestone=mid)
    print(" task:", role, "->", r.get("task_id", r))

for t, s, why in [
    ("URP not HDRP", "Ship on URP, stylized-realistic.",
     "User: 'Unity cok kasiyor'. HDRP would make it worse. URP + good "
     "lighting/post hits realistic enough at 60fps on weak GPU."),
    ("Hand-built valley before procedural", "Vertical slice is one "
     "hand-crafted valley; procedural generation is post-slice.",
     "Procedural first = unshippable scope. Prove the loop by hand."),
    ("Forgiving combat", "Dodge window generous, night wave beatable "
     "first try with care.", "It's a 2h kafa-dagitma game, not a "
     "soulslike. Remnant feel, not Remnant difficulty."),
    ("Bounded fog rule", "Fog linear 15-70m, never exp^2 high density.",
     "Root-caused the blank-teal-void: unbounded fog ate the frame."),
]:
    print(" decision:", studio_propose_decision(title=t, summary=s, rationale=why).get("decision_id"))

print("PLAN DONE")
