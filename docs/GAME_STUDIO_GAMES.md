# Game Studio — Games & Gameplay Catalog

What the autopilot can author beyond decorating scenes: **gameplay**. This page is the
reference for the game blueprints, the behaviour catalog, and how to drive them.
Everything here is verified against the code by `tests/test_games_doc.py` (no phantom
names).

## 1. Game types (blueprints)

`unity_build_simple_game(game_type=…, collectible_count=N, execute=False)` plans (and
optionally builds) a complete playable game by composing the building blocks below.

| game_type | What it is | Example command (tr / en) |
|-----------|-----------|----------------------------|
| `collectathon` | Ground + WASD player + an on-screen **score HUD** + N collectibles (each +1) + a goal zone | "bana bir toplama oyunu kur" / "build me a collectathon game" |
| `dodge` | Ground + WASD player + N **moving** hazards (mover+killzone) + goal | "dodge oyunu yap" / "make a dodge game" |
| `survival` | Ground + WASD player + N elevated hazard **spawners** (raining cubes) | "sağ kalma oyunu kur" / "build me a survival game" |
| `platformer` | Ground + WASD+**jump** player + N solid platforms climbing like a staircase + a goal on top. Every **other** ledge (the odd ones; the first is safe) carries a moving **hazard** (`patrol` ping-pongs it across at player height + `killzone` respawns you on touch) -- time your jump for when it's at the far end. No new behaviour | "platform oyunu yap" / "build me a platformer" |
| `chase` | Ground + player + score HUD + N enemies that **chase** you (follow + killzone) + N collectibles to grab while escaping + goal | "kovalamaca oyunu kur" / "build me a chase game" |
| `maze` | A deterministic, always-solvable procedural **labyrinth** (seeded): solid walls + player at the entrance + goal at the exit, with a **killzone trap in every dead-end** cell. In a perfect maze the dead-ends are guaranteed OFF the unique solution path (`core.maze.maze_dead_end_cells`), so the traps never block it — a wrong turn just respawns you. `collectible_count` is the maze size (3–8) | "labirent oyunu kur" / "build me a maze game" |
| `arena` | A blocky **brawler**: an armed player (health + attack + score + xp + inventory) versus N enemies that chase and attack back (enemy AI + reward), PLUS a single high-HP **mini-boss** across the arena (the `boss` behaviour, tagged Enemy, with its own HP bar) — the climax you whittle down while the swarm pressures you; clear the swarm **and** the boss to WIN. No goal | "arena oyunu kur" / "dövüş oyunu yap" / "build me a brawler" |
| `horde` | A **survival-brawler**: a fully-armed player (health/attack/ranged/xp/inventory) vs **escalating waves** of enemies from a central spawner + scattered loot | "horde oyunu kur" / "dalga modu" / "akın oyunu" / "survival brawler" |
| `runner` | An **endless runner** (the first non-arena-style type): an **auto-running** player (forward +Z, A/D strafe, Space jump) + a distance **score** it feeds itself + N weaving `killzone` obstacles that snap you back to the start on touch. Endless — no goal/win, get as far as you can | "runner oyunu kur" / "endless runner yap" / "koşu oyunu" |
| `tower_defense` | A **tower-defense**, all from existing blocks: enemies march to a **Base** (tagged Player + `health`, so the existing enemy AI targets it; it falls → **lose**), defended by a line of `ranged` **towers** (auto-target the nearest enemy) + a mobile **hero** (`player`+`attack`, not tagged Player so enemies ignore it). A `horde` wave **spawner** on the far side rains escalating waves that also march at the base, so it's a real escalating defense. **Win** when all enemies are cleared. title/win-lose/sound | "tower defense oyunu kur" / "kule savunma yap" / "td oyunu" |
| `time_survival` | **Outlast the clock**: an armed player vs N enemies + a GameManager `timer`. When the countdown ends the timer SendMessages "Survived" and `gameover` declares a **WIN** (you survived); clearing every enemy early also wins; dying **loses**. Distinct from `survival` (which never ends) | "zamana karşı oyun" / "süreli hayatta kalma" / "survive the clock" |
| `stealth` | A **stealth** game, the first won by **avoiding** combat: slip past N patrolling guards (`patrol` + a `detector` line-of-sight) and reach the **goal** exit. A detector that sees you SendMessages "PlayerDied" (**LOSE**); reaching the goal SendMessages "ReachedGoal" (**WIN**). Guards are NOT tagged Enemy, so you can't (and needn't) fight them | "stealth oyunu kur" / "gizlilik oyunu" / "gizli geç" |
| `puzzle` | A **sokoban** -- a push mechanic, no combat/timer: a WASD player shoves N `pushable` crates onto N target markers on an open floor. The hidden GameManager `puzzle` win-manager finds `Crate_*`/`Target_*` **by name** (no custom Unity tags) and **WINS** once every target is covered. Always solvable (open arena) | "puzzle oyunu kur" / "sokoban yap" / "kutu itme" |
| `hold` | **King of the hill** -- won by HOLDING a position, not fighting: the player (movement + `health`, NO attack) stands in a central `holdzone` to fill a meter while N enemies chase + attack to push them out. Full meter -> the zone SendMessages "Survived" -> **WIN**; dying -> **LOSE**. Since the player can't attack, holding is the only win | "king of the hill" / "bölge tut" / "hold the zone" |
| `escort` | An **escort / VIP mission** -- won by PROTECTING something that isn't you: the Escort VIP (a Capsule tagged **Player**, so the existing enemy AI marches at IT -- the tower-defense inversion with a MOVING base) walks itself to the goal (the new `escort` behaviour) and carries `health` (destroyed -> **LOSE**). You drive a separate, untagged Hero bodyguard (`player` + `attack` + score) who clears the N enemies before they kill the VIP. Delivering the VIP SendMessages "ReachedGoal" **or** clearing every enemy -> **WIN** | "escort oyunu kur" / "refakat görevi" / "vip escort game" |
| `boss` | A **boss fight** -- the first sustained single-target DUEL (one tough foe, not a swarm): an armed player (movement + `health` + melee `attack` + `ranged` so you can chip it at distance + score + xp) duels N `boss` foes (tag Enemy). Each `boss` chases + melee-attacks, has a big HP pool with an on-screen HP bar, and on death grants big XP + **destroys itself** so `gameover`'s clear-all-enemies **WIN** fires; the boss killing you **LOSES**. `boss_count` is the number of bosses (1 = a clean duel, >1 = a boss rush) | "boss oyunu kur" / "patron savaşı" / "boss arena" |
| `collector_race` | A **collector race** -- the first type where the CLOCK is your enemy: a WASD player + score HUD races to grab all N `Collectible_*` before a countdown runs out. The hidden GameManager runs the new `collectrace` manager -- it counts the remaining collectibles **by name** (decoupled) and SendMessages "ReachedGoal" (**WIN**, reusing `gameover`'s hook) the instant the last is gone, or "PlayerDied" (**LOSE**) if the clock hits zero first. Distinct from `collectathon` (no clock) and `time_survival` (the timer is a WIN) | "collector race" / "toplama yarışı" / "süreli toplama" |
| `twin_stick` | A **twin-stick shooter** -- the first RANGED-PRIMARY type: a lean kiter (movement + `health` + a `ranged` auto-aim weapon + score, **no melee attack**) backs away from a ring of N enemies (enemy AI + reward, tag Enemy) while the gun mows them down. **WIN** by clearing the ring (`gameover`'s enemy-clear), **LOSE** if they corner and kill you. Distinct from `arena` (melee brawler with xp/loot + a mini-boss) and `horde` (full kit + a wave spawner) | "twin stick oyunu kur" / "twinstick" / "top down shooter" |

`collectible_count` is the count of the main repeated element (collectibles / hazards /
spawners / platforms / enemies). The blueprint registry is `core/game_blueprint.BLUEPRINTS`;
`list_blueprints()` lists them and `plan_game(game_type, count)` dispatches.

## 2. Gameplay behaviour catalog

Give one object a behaviour with `unity_add_gameplay_behaviour(object, behaviour)`
(physics, composed from existing tools) or `unity_add_script_behaviour` /
`unity_apply_script_behaviour` (scripted, generates a MonoBehaviour).

### Physics (no script — composes Rigidbody/collider, applies instantly)
| behaviour | Effect |
|-----------|--------|
| `physics` / `falling` | Gravity-driven rigid body + collider |
| `heavy` | Physics with high mass |
| `floaty` | Physics with high drag |
| `kinematic` | Kinematic body (script-moved platform) |
| `static_obstacle` | Collider only — a solid, non-moving obstacle |

### Scripted (generates a MonoBehaviour — needs a Unity recompile to attach)
| behaviour | Class | Effect |
|-----------|-------|--------|
| `rotate` / `spin` / `spinner` | AutopilotRotator | Spins every frame |
| `move` / `mover` | AutopilotMover | Translates every frame |
| `player` / `controller` | AutopilotPlayerController | WASD movement + Space jump |
| `collectible` | AutopilotCollectible | OnTriggerEnter(Player) → +1 score (SendMessage) **immediately**, then a short scale-up **"pop"** (`popTime`/`popScale`, Time-driven) before Destroy — juice on the collect moment. A `collected` guard scores exactly once; deterministic, decoupled |
| `goal` | AutopilotGoalZone | OnTriggerEnter(Player) → win flag |
| `killzone` | AutopilotKillZone | OnTriggerEnter(Player) → respawn |
| `spawner` | AutopilotSpawner | InvokeRepeating spawns physics cubes (waves) |
| `score` / `skor` / `puan` / `hud` | AutopilotScore | Global counter + top-left OnGUI HUD; `Add(n)` static or `SendMessage("AddScore", n)` |
| `bob` | AutopilotBob | Bobs up/down on a sine wave around its start position |
| `bounce` / `zıpla` | AutopilotBounce | Bounces off its rest height (abs-sine, never dips below) |
| `patrol` / `devriye` | AutopilotPatrol | Patrols back and forth between two points (PingPong) |
| `follow` / `chase` / `takip` | AutopilotFollower | Chases the Player (tag) with MoveTowards; no-op if absent |
| `orbit` | AutopilotOrbit | Orbits its start point on an axis (RotateAround) |
| `wander` | AutopilotWander | Drifts to random points near home, re-targeting on a timer |
| `health` / `can` / `sağlık` / `hp` | AutopilotHealth | Hit points + `TakeDamage(n)`/`Heal(n)`; death → respawn (or destroy); top-right HP HUD |
| `attack` / `saldırı` / `vur` / `hit` | AutopilotAttack | Damages a tagged target in `range` every `cooldown` via `SendMessage("TakeDamage")` — pairs with `health`, no hard reference |
| `enemy` / `düşman` / `mob` | AutopilotEnemy | Chases the Player (MoveTowards) and, in `attackRange`, attacks on a cooldown (`SendMessage("TakeDamage")`) — chase + attack in one, decoupled |
| `xp` / `seviye` / `level` / `tecrübe` | AutopilotXP | Experience + leveling: `Add(n)` static or `SendMessage("AddXP", n)`; levels up at `Level*100` XP; top-right "Lv N - XP" HUD |
| `reward` / `ödül` / `ganimet` | AutopilotReward | A killable enemy's HP + loot: takes damage, and on death grants `xpReward` to the Player (`SendMessage("AddXP")`) and destroys itself |
| `loot` / `item` / `eşya` | AutopilotLoot | An item pickup (trigger): on Player touch, `SendMessage("AddItem")` then destroy |
| `inventory` / `envanter` / `çanta` | AutopilotInventory | Item count + HUD: `Add(n)` static or `SendMessage("AddItem", n)`; top-left "Items: N" |
| `ranged` / `menzilli` / `nişan` / `ateş` | AutopilotRanged | A ranged attack (gun/bow): every `cooldown`, hits the **nearest** tagged target within a long `range` via `SendMessage("TakeDamage")`, aiming at it |
| `horde` / `akın` | AutopilotHorde | A survival-brawler driver: spawns **escalating waves** of enemies (Enemy tag + enemy AI + reward) over time, up to `maxWaves` (needs AutopilotEnemy + AutopilotReward in the project) |
| `gameover` / `oyunsonu` / `sonekran` | AutopilotGameOver | Win/lose state + end screen: **WIN** when no `Enemy` remain, **LOSE** on `SendMessage("PlayerDied")`; pauses and shows "YOU WIN"/"GAME OVER", press R to restart |
| `title` / `başlık` / `menu` / `anaekran` | AutopilotTitle | Start/title screen: draws `titleText` + "Press SPACE to start", holds the game **paused** until Space. Pauses via `Time.timeScale = 0` in **Start** (not Awake) so it wins over `gameover`'s Awake reset — Unity runs all Awakes before any Start, so the game reliably begins on the title screen |
| `sound` / `ses` / `audio` / `beep` / `sfx` | AutopilotSound | A **procedural** sound cue, honest about being generate-only: ships **no** audio asset and loads nothing from Resources — it **builds** its clip at runtime via `AudioClip.Create` + a deterministic `Mathf.Sin` sine wave. Decoupled: fire it with `SendMessage("PlayCue")` (optionally a frequency). `arena`/`horde` wire the `title`/`gameover` bookends; `sound` is available as a cue for any object |
| `runner` / `koşu` / `endless` | AutopilotRunner | An endless-runner controller: **auto-runs forward** (+Z) at `runSpeed`, A/D strafe, Space jump (gravity arc, no Rigidbody). Decoupled distance score: every `scoreInterval` it `SendMessage("AddScore", 1)` to itself so an `AutopilotScore` on the same object ticks up (no-op without one). Deterministic — no `Math.random` |
| `timer` / `süre` / `zaman` / `countdown` | AutopilotTimer | A **countdown** timer + HUD: counts `duration` seconds down (freezes while paused), draws the remaining time top-right, and on zero fires once a decoupled `SendMessage("Survived")` — a **win signal** `AutopilotGameOver` reacts to ("outlast the clock"). Deterministic (reads only `Time.deltaTime`) |
| `detector` / `dedektör` / `görüş` / `nöbetçi` | AutopilotDetector | A guard's **line-of-sight**: each frame finds the Player and, if within `sightRange`, SendMessages "PlayerDied" to the `GameManager` (caught → **lose**) — decoupled, by name, fires once. Pair with `patrol` for a moving guard (the `stealth` game does). Deterministic (only distance) |
| `pushable` / `kutu` / `crate` / `itilebilir` | AutopilotPushable | A **pushable crate** (sokoban): when the Player comes within `pushRange` it slides one notch **away** (push it onto a target). Decoupled (finds the Player by tag), deterministic — only positions, no physics tuning, no custom tags. Name crates `Crate_*` so the puzzle manager scores them |
| `puzzle` / `bulmaca` / `sokoban` | AutopilotPuzzle | A **sokoban win manager**: finds every `Target_*` and `Crate_*` **by name** (no custom tags, no hard refs), draws "Crates: covered/total", and **WINS** once every target has a crate within `coverRange` (pauses, beeps via decoupled `PlayCue`, R restarts). Deterministic |
| `holdzone` / `hold` / `bölge` / `tepe` | AutopilotHoldZone | A **capture/hold zone** (king of the hill): while the Player is within `radius`, a meter fills; at `holdTime` it SendMessages "Survived" to the GameManager (decoupled, reuses the win hook) — stepping out pauses the fill. Draws "Hold: filled/target". Deterministic (positions + time) |
| `escort` / `eskort` / `refakat` / `vip` | AutopilotEscort | An **escort VIP**: walks ITSELF toward a goal object (found by name, decoupled) via `MoveTowards` and on arrival fires a one-time `SendMessage("ReachedGoal")` to the GameManager (the **WIN**). Tag it **Player** so the enemy AI marches at it (and a goal zone fires the same win); pair with `health` so destroying it **LOSES**. Deterministic — only positions, no RNG |
| `boss` / `patron` | AutopilotBoss | A **boss**: a single high-HP foe for a duel. Chases the Player + melee-attacks on a cooldown (like the enemy AI) but with a big HP pool you whittle down; takes damage via `SendMessage("TakeDamage")`; on death grants `xpReward` (`SendMessage "AddXP"`) and **destroys itself** so `gameover`'s clear-all-enemies WIN fires (tag it Enemy). Draws a boss HP bar across the top. Decoupled, deterministic (distance + time, no RNG) |
| `collectrace` / `yarış` | AutopilotCollectRace | A **collector-race manager**: each frame counts objects named `Collectible_*` **by name** (decoupled, no tags); when the last is gone it SendMessages a one-time "ReachedGoal" (**WIN**, reusing `gameover`'s hook), and if its countdown reaches zero first it SendMessages "PlayerDied" (**LOSE** -- the studio's first losing deadline). Draws "Collected got/total" + the remaining time. Deterministic (counts + `Time.deltaTime`, no RNG) |
| `turret` / `taret` | AutopilotTurret | A **stationary turret**: every `cooldown` seconds it finds the Player within `range`, aims at it, and damages it via `SendMessage("TakeDamage")` (decoupled, no-op if the player has no health). It does **not** move and is **not** tagged Enemy, so you survive it by **dodging** to the goal, not by killing it (a 'run the gauntlet' threat). Composer element: `turret` -> the player gains `health` + a goal is auto-added. Deterministic (distance + time, no RNG) |
| `hitflash` / `parlama` / `flash` | AutopilotHitFlash | Visual **hit feedback** (juice): on `SendMessage("TakeDamage")` the renderer flashes `flashColor` then lerps back over `flashTime`. Purely cosmetic + decoupled -- runs alongside the real damage handler (boss/health/reward). Wired onto **bosses** (the `boss` type + the arena mini-boss), where the high HP makes the repeated flash visible. Deterministic (only `Time`, no RNG); a no-op without a Renderer |

These are the **action-RPG combat & progression** building blocks (P11): `attack`/`enemy` deal damage
that `health`/`reward` receive, a killed `reward` grants XP that `xp` levels up on, and `loot`/`inventory`
add an item economy — all fully decoupled (SendMessage, no hard type reference). The `arena` game wires
the combat loop: attack → reward dies → XP → level up. Turkish/English aliases are accepted (fizik, ağır, oyuncu,
toplanabilir, hedef, ölüm/lava, dalga, devriye, takip, zıpla, can, saldırı, …). **Every behaviour
listed here is templated** — each generates a compilable MonoBehaviour (`generate_behaviour_script`
returns its source); none are stubs.

## 3. "Build me a game" — intent routing

`plan_unity_fast_action` (and the Unity fast-path) route these to a `unity_build_simple_game`
plan automatically:

- tr: "oyun kur", "oyun yap", "toplama oyunu", "dodge/kaçma oyunu", "sağ kalma / hayatta kalma oyunu", "platform / zıplama oyunu", "kovalamaca / takip oyunu", "labirent oyunu", "arena / dövüş / savaş oyunu", "horde / dalga modu / akın / survival brawler", "runner / koşu oyunu / endless", "tower defense / kule savunma / td", "zamana karşı / süreli hayatta kalma", "stealth / gizlilik / gizli geç", "puzzle / sokoban / kutu itme", "king of the hill / bölge tut", "escort / refakat / vip", "boss / patron / boss arena", "collector race / toplama yarışı / süreli toplama", "twin stick / twinstick / top down shooter", "oyun iskeleti"
- en: "build me a game", "make a collectathon/dodge/survival/platformer/chase/maze/arena/horde/runner/tower_defense/time_survival/stealth/puzzle/hold/escort/boss/collector_race/twin_stick game"

A number in the prompt sets the count ("toplama oyunu yap 8 toplanabilir" → 8).

**Seed (reproducible variety):** add "tohum 42" / "seed 42" / "seed:abc" (or "42 tohumuyla") to a
build to make the layout reproducible — the same seed always builds the same game, a different seed a
different (but deterministic) one. The seed is recognised separately from the count, so "zor dodge
oyunu kur tohum 7" is difficulty-hard (8) with seed 7. The seed is recorded in the plan and survives
save/load and export, so seeded games are shareable.

**Assess (don't build):** "oyunu değerlendir", "dodge oyununu analiz et", "oynanabilir mi",
"assess the game", "is the game playable" route to `unity_assess_game` instead — a read-only
readiness report (counts + playable verdict + warnings, no scene changes, no bridge). The assess
intent is checked *before* the build intent, so a prompt with both a game type and an assess verb
("dodge oyununu değerlendir") is analysed, not rebuilt. Scene-level "analiz"/"qa"/"performans"
(no game context) still route to the visual-QA / profiling tools.

**Save / load / list (P8 persistence):**
- "oyunu kaydet", "dodge oyununu **boss olarak** kaydet", "save the game **as** level1",
  `kaydet "my level"` → `unity_save_game` (writes a JSON file under the games directory; the name is
  taken from quotes / "as X" / "X olarak", else the game type, and is sanitized + traversal-guarded).
- "oyunu yükle boss", "boss oyununu yükle", "load game level1" → `unity_load_game` (returns the saved
  **plan only** — it does not build it).
- "kayıtlı oyunlar", "saved games", "diskteki oyunlar" → `unity_list_saved_games`.

These use distinctive verbs (kaydet/yükle/kayıtlı/save/load) and are checked before build, so
"dodge oyununu kaydet" saves rather than rebuilds; "kayıtlı oyunlar" (disk) stays distinct from
"hangi oyunlar" (catalog). Scene-level "save"/"geri yükle" without a game context are not touched.

## 4. execute=False vs execute=True (recompile note)

- `execute=False` (default): returns the **step plan** only. No scene changes — safe to call
  anytime, including unattended.
- `execute=True`: builds the geometry and imports the behaviour scripts. **Importing a script
  reloads the Unity domain (a recompile)**, which briefly drops the bridge — run it with the
  editor in focus. The execute path imports each *unique* behaviour script once
  (`group_execution_plan`) to collapse N recompiles into one.

## 5. Adding a new blueprint

1. Write `plan_<name>_game(count, ...)` in `core/game_blueprint.py` returning
   `{ok, game, summary, steps}` (steps are `{tool, kwargs}` or `{script_behaviour:{object, behaviour}}`).
2. Register it: `BLUEPRINTS["<name>"] = plan_<name>_game`.
3. Add an intent trigger to `plan_unity_fast_action`'s build-game block.
4. Add a row to the table in §1 and a test.

## 6. Difficulty variations

`unity_game_variations(game_type, counts="3,5,8")` builds the **same** game at several counts and
attaches a readiness summary to each — easy/medium/hard difficulty options the studio can offer
before committing to a build. Pure analysis (no scene changes, no bridge); the pure planner is
`core/game_blueprint.plan_game_variations`. Counts are deduped, clamped (≥1) and sorted ascending
so difficulty rises monotonically (more enemies/collectibles → more objects). Each entry reports
`{label, params, summary, object_count, unique_scripts, playable, warnings}`.

**Intent routing:**
- A **difficulty word** in a build prompt sets the count: kolay/easy → 3, orta/normal/medium → 5,
  zor/hard → 8. An explicit number always wins ("zor dodge oyunu yap 4" → 4). ("çok" is not a
  difficulty trigger — it's a quantity word; "çok zor" still matches "zor".)
- **"varyasyon" / "seçenekler" / "farklı zorluklar" / "variations"** (with a game type) route to
  `unity_game_variations` instead of building — checked before the build intent, so "dodge
  varyasyonları göster" lists the options rather than building one dodge.

## 7. Game catalog (what can I make?)

`unity_game_catalog()` returns a one-glance report of the whole catalog: every game type's summary,
object/script counts, player/goal/score flags, playable verdict, and warnings, plus the full set of
behaviours used across all games and whether they are `all_playable`. Pure (no scene changes, no
bridge); the pure function is `core/game_qa.summarize_catalog`. Routed by intent — "oyun katalogu",
"hangi oyunlar yapabilirsin", "neler yapabilirsin", "what games can you make", "list games" — while
bare "katalog" still means the *scene* catalog (`unity_get_scene_catalog`).

`unity_game_showcase()` is the discovery counterpart: a "say this -> get this game" gallery that, for
every game type, gives the example natural-language prompt that builds it, a one-line pitch, and its
object count. Each example is verified **live** to route to its own build (`core/game_qa.showcase_routing`),
so the showcase doubles as a regression guard for the whole NL-intent layer -- break any game's detection
and it (and its test) go red. Pure; routed by intent — "örnek oyunlar", "örnek göster", "show me examples",
"game examples". The pure function is `core/game_qa.build_game_showcase`.

`unity_game_anatomy(game_type)` zooms IN on a single game type: its size (object + unique-script counts),
its behaviours grouped by category (control / movement / world / combat / progression / game feel /
physics), the build phases (geometry -> import each unique script once -> attach), the playability verdict
+ any design notes, and the example prompt. Code-derived from `plan_game` + `assess_game_readiness` +
`group_execution_plan`, so it never drifts. Routed by intent — "arena oyununun yapısı", "X oyunu
anatomisi", "breakdown of the X game", "X neyden oluşuyor". The pure function is
`core/game_qa.build_game_anatomy`.

## 8. Living scenes (decorative, not a game)

Not every scene is a game. `unity_animate_group` brings a scene to life: it places N props
and gives each a **decorative** scripted behaviour (`bob` / `orbit` / `rotate` / `wander`,
cycled) so the scene breathes — pure juice, no player or goal. The pure planner is
`core/game_blueprint.plan_ambient_decor` (default decor set `DECOR_BEHAVIOURS`); the tool wraps
it with the same `execute=False` (default, plan only) / `execute=True` (build + one recompile)
contract as the games.

| Tool | What it does | Example command |
|------|--------------|-----------------|
| `unity_animate_group` | Place N props + cycle decorative behaviours over them (living scene) | "sahneyi canlandır" / "animate the scene" / "yaşayan sahne kur" |

`behaviours` is an optional comma-separated subset (e.g. `"bob,rotate"`); unknown names are
normalized and dropped so the plan never references a behaviour without a template.

> See `GAME_STUDIO_TOOLS.md` for the full tool catalog and `GAME_STUDIO_PROGRESS.md` for the
> per-cycle history of how this was built.
