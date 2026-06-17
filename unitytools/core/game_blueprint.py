"""Game blueprints — compose the gameplay building blocks into a playable game.

The peak of the "scene decorator -> game maker" arc: instead of one object at a
time, plan a whole minimal game. plan_collectathon_game emits an ordered list of
steps that reuse the existing tools (primitives, placement, tag) and scripted
behaviours (player controller, collectible, goal). Pure + deterministic; the
unity_build_simple_game tool turns it into actions (opt-in, since script behaviours
trigger Unity recompiles).

A step is either:
  * {"tool": "<unity_tool>", "kwargs": {...}}        — a direct tool call
  * {"script_behaviour": {"object": str, "behaviour": str}}  — attach a MonoBehaviour
"""
from __future__ import annotations

from typing import Any


def plan_collectathon_game(collectible_count: int = 5, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a minimal collect-a-thon: ground, a controllable player, N pickups, a goal.

    Returns {ok, game, summary, collectible_count, steps}. Deterministic — no I/O.
    """
    n = max(1, min(int(collectible_count), 50))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player: cube, tagged Player, with the WASD controller behaviour and the
    #    score HUD (collectibles message the player to add points, so the counter
    #    lives on the player — one persistent object, no stray HUD GameObject).
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})

    # 3) collectibles: N spheres in a ring, each a pickup trigger
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Sphere",
            "count": n,
            "pattern": "circle",
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Collectible",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Collectible_{i}", "behaviour": "collectible"}})

    # 4) goal zone
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "collectathon",
        "summary": f"Collect-a-thon: ground + WASD player + score HUD + {n} collectibles + goal ({len(steps)} steps).",
        "collectible_count": n,
        "steps": steps,
    }


def plan_dodge_game(obstacle_count: int = 6, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a dodge game: ground, a controllable player, N MOVING hazards, a goal.

    Each hazard composes two behaviours (mover + killzone) so it slides around and
    respawns the player on contact — a different game from the same building blocks.
    Same return schema as plan_collectathon_game.
    """
    n = max(1, min(int(obstacle_count), 50))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "scatter",
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Obstacle",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Obstacle_{i}", "behaviour": "mover"}})
        steps.append({"script_behaviour": {"object": f"Obstacle_{i}", "behaviour": "killzone"}})

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "dodge",
        "summary": f"Dodge: ground + WASD player + {n} moving hazards + goal ({len(steps)} steps).",
        "obstacle_count": n,
        "steps": steps,
    }


def plan_survival_game(spawner_count: int = 3, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a survival game: ground, a controllable player, M elevated spawners that
    rain physics-cube hazards in waves. Survive the onslaught. Same return schema.
    """
    n = max(1, min(int(spawner_count), 20))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(4.0, size / float(n)),
            "origin_y": 6.0,           # elevated so spawned cubes fall onto the arena
            "name_prefix": "Spawner",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Spawner_{i}", "behaviour": "spawner"}})

    return {
        "ok": True,
        "game": "survival",
        "summary": f"Survival: ground + WASD player + {n} hazard spawners ({len(steps)} steps).",
        "spawner_count": n,
        "steps": steps,
    }


def plan_platformer_game(platform_count: int = 5, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a platformer: ground, a WASD+jump player, N solid platforms climbing
    like a staircase, and a goal at the top you reach by jumping up them.

    The player already has a Space-to-jump controller; the platforms are plain
    cubes (which carry a BoxCollider) made explicitly solid with the
    ``static_obstacle`` physics behaviour, so they are jump-on-able and need no
    recompile. Each platform sits a step higher (and further) than the last.
    Same return schema as the other plan_*_game blueprints.
    """
    n = max(1, min(int(platform_count), 30))
    size = max(6.0, float(arena_size))
    step_y = 1.5   # how much higher each platform sits
    step_z = 3.0   # how much further out each platform sits (staircase depth)
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player at the foot of the staircase: WASD + Space jump
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    # 3) platforms: cubes climbing up-and-away, each a solid (static_obstacle) ledge
    top_y = 0.0
    top_z = 0.0
    for i in range(n):
        py = 1.0 + i * step_y
        pz = (i + 1) * step_z
        top_y, top_z = py, pz
        steps.append({
            "tool": "unity_create_primitive",
            "kwargs": {"type": "Cube", "name": f"Platform_{i}", "position_y": py, "position_z": pz},
        })
        steps.append({
            "tool": "unity_add_gameplay_behaviour",
            "kwargs": {"object_name": f"Platform_{i}", "behaviour": "static_obstacle"},
        })

    # 4) goal sitting on top of the last (highest) platform
    steps.append({
        "tool": "unity_create_primitive",
        "kwargs": {"type": "Cube", "name": "Goal", "position_y": top_y + 1.0, "position_z": top_z},
    })
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "platformer",
        "summary": f"Platformer: ground + WASD+jump player + {n} climbing platforms + goal on top ({len(steps)} steps).",
        "platform_count": n,
        "steps": steps,
    }


def plan_chase_game(enemy_count: int = 4, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a chase game: ground, a WASD+jump player with a score HUD, N enemies
    that CHASE the player (follow + killzone — touch you and you respawn), and a
    ring of collectibles to grab while you run. Showcases the new `follow`
    behaviour combined with `killzone` (the same compose-two-behaviours trick the
    dodge game uses for moving hazards). Same return schema as the others.
    """
    n = max(1, min(int(enemy_count), 30))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player: tagged, controllable, carrying the score HUD
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})

    # 3) enemies: a ring of cubes that chase the player and respawn it on contact
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(3.0, size / float(n)),
            "name_prefix": "Enemy",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "follow"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "killzone"}})

    # 4) collectibles: a tighter ring to grab while escaping (+1 each to the HUD)
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Sphere",
            "count": n,
            "pattern": "circle",
            "spacing": max(2.0, size / (2.0 * float(n))),
            "name_prefix": "Collectible",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Collectible_{i}", "behaviour": "collectible"}})

    # 5) goal zone
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    return {
        "ok": True,
        "game": "chase",
        "summary": f"Chase: ground + WASD player + score HUD + {n} chasing enemies + {n} collectibles + goal ({len(steps)} steps).",
        "enemy_count": n,
        "steps": steps,
    }


def plan_arena_game(enemy_count: int = 4, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan an arena/brawler: an armed player versus N attacking enemies — the
    first game to wire the action-RPG combat trio (health + attack + enemy).

    The player (tag Player) gets WASD movement, health, a melee attack (its default
    targetTag is "Enemy"), a score HUD, and xp/leveling. Each enemy (tag Enemy) gets
    the enemy AI (chase + attack the Player) and a `reward` (its HP + XP loot): the
    player can kill them — on death they grant XP to the player and are destroyed —
    and they can hurt the player back. There is no goal: you fight and level up.
    Across the arena sits a single MINI-BOSS (the high-HP `boss` behaviour, also tagged
    Enemy, with its own HP bar) — the climax you whittle down while the swarm pressures
    you; clearing the swarm AND the boss is the WIN. Same step schema as the other
    blueprints; the seed (via plan_game) jitters the enemy ring.
    """
    n = max(1, min(int(enemy_count), 30))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) the armed player: movement + health + attack (hits "Enemy") + score + xp
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "health"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "attack"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "xp"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "inventory"}})

    # 3) enemies: a ring of cubes tagged Enemy, each chasing+attacking the player and
    #    carrying a `reward` (their HP + XP loot) so the player can defeat them and
    #    level up. Only `reward` (not `health`) is on the enemy, so the player's
    #    attack does single damage to one TakeDamage receiver.
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(3.0, size / float(n)),
            "name_prefix": "Enemy",
        },
    })
    for i in range(n):
        steps.append({"tool": "unity_set_tag", "kwargs": {"name": f"Enemy_{i}", "tag": "Enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "reward"}})

    # 3b) a single MINI-BOSS across the arena: an elite among the swarm. It is tagged Enemy
    #     (so the same clear-all-enemies WIN includes it) and runs the high-HP `boss`
    #     behaviour (chases + melee-attacks, draws a boss HP bar, grants big XP on death and
    #     destroys itself). Named "Boss" (NOT "Enemy_*") so it stays a distinct elite. This
    #     is the climax: whittle down the boss while the swarm pressures you.
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Boss", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Boss", "tag": "Enemy"}})
    steps.append({"script_behaviour": {"object": "Boss", "behaviour": "boss"}})
    steps.append({"script_behaviour": {"object": "Boss", "behaviour": "hitflash"}})  # juice: flash on hit

    # 4) loot scattered on the field: spheres the player picks up for items while
    #    fighting (a simple, decoupled item economy — collect -> inventory HUD).
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Sphere",
            "count": n,
            "pattern": "scatter",
            "spacing": max(2.0, size / (2.0 * float(n))),
            "name_prefix": "Loot",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Loot_{i}", "behaviour": "loot"}})

    # 5) a hidden GameManager that bookends the game. `title` shows a start screen and
    #    holds it paused until Space (pauses in Start, so it wins over gameover's Awake
    #    un-pause); `gameover` ends it: WIN when all enemies are cleared, LOSE when the
    #    player dies (its health signals "PlayerDied" to this object). Position is
    #    irrelevant for both (screen-space OnGUI + global timeScale + Input).
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "title"}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "gameover"}})
    # a procedural sound cue on the same object: gameover SendMessages "PlayCue" on the
    # win/lose transition (decoupled, no-op if absent), so the end has audio feedback
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "sound"}})

    return {
        "ok": True,
        "game": "arena",
        "summary": f"Arena: ground + armed WASD player (health+attack+score+xp+inventory) + {n} enemies (chase+attack, reward XP) + a mini-boss + {n} loot ({len(steps)} steps).",
        "enemy_count": n,
        "steps": steps,
    }


def plan_horde_game(enemy_count: int = 4, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a horde / survival-brawler: a fully-armed player versus ESCALATING waves
    of enemies driven by a central wave spawner (the action-RPG "horde" mode).

    The player (tag Player) gets the full combat kit (player + health + attack +
    ranged + score + xp + inventory). A central `Spawner` object runs the `horde`
    behaviour, which spawns growing waves of enemies (each tagged Enemy, with the
    enemy AI + reward). One initial enemy is placed up front so the game starts
    populated AND so AutopilotEnemy.cs + AutopilotReward.cs are imported (the horde
    spawner AddComponents them). `enemy_count` sets the number of `loot` pickups
    scattered on the field. Same step schema as the others; the seed jitters loot.
    """
    n = max(1, min(int(enemy_count), 30))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) the fully-armed player, off to one side of the arena
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5, "position_z": -size / 3.0}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    for b in ("player", "health", "attack", "ranged", "score", "xp", "inventory"):
        steps.append({"script_behaviour": {"object": "Player", "behaviour": b}})

    # 3) a central wave spawner that rains escalating enemy waves
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Spawner", "position_y": 0.5}})
    steps.append({"script_behaviour": {"object": "Spawner", "behaviour": "horde"}})

    # 4) one initial enemy so AutopilotEnemy.cs + AutopilotReward.cs are imported
    #    (the horde spawner AddComponents them) and the arena starts populated
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Enemy_0", "position_y": 0.5, "position_z": size / 3.0}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Enemy_0", "tag": "Enemy"}})
    steps.append({"script_behaviour": {"object": "Enemy_0", "behaviour": "enemy"}})
    steps.append({"script_behaviour": {"object": "Enemy_0", "behaviour": "reward"}})

    # 5) loot scattered on the field to grab while you survive
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Sphere",
            "count": n,
            "pattern": "scatter",
            "spacing": max(2.0, size / (2.0 * float(n))),
            "name_prefix": "Loot",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Loot_{i}", "behaviour": "loot"}})

    # 7) a hidden GameManager bookend: `title` shows a start screen (paused in Start,
    #    so it wins over gameover's Awake un-pause), `gameover` ends it: WIN when all
    #    waves are cleared, LOSE when the player dies (health signals "PlayerDied"). Both
    #    are position-independent (screen-space OnGUI + global timeScale + Input).
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "title"}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "gameover"}})
    # a procedural sound cue on the same object: gameover SendMessages "PlayCue" on the
    # win/lose transition (decoupled, no-op if absent), so the end has audio feedback
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "sound"}})

    return {
        "ok": True,
        "game": "horde",
        "summary": f"Horde: armed player (health+attack+ranged+xp+inventory) + a central wave spawner (escalating enemy waves) + {n} loot ({len(steps)} steps).",
        "enemy_count": n,
        "steps": steps,
    }


def plan_runner_game(obstacle_count: int = 8, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan an endless runner: the first non-arena-style game type.

    The player auto-runs FORWARD (the `runner` behaviour) and dodges a weaving lane
    of obstacles by strafing (A/D) and jumping (Space). Distance is the score: the
    runner SendMessages "AddScore" each second to its own `score` HUD (decoupled).
    Each obstacle is a `killzone` trigger — touching one snaps the player back to the
    start (lose your run), so the goal is to get as far as possible. Endless: there is
    no win condition, so no goal/gameover. Same return schema as the other blueprints.
    """
    n = max(1, min(int(obstacle_count), 50))
    gap = max(3.0, float(arena_size) / 4.0)   # spacing between obstacles along the track
    lanes = (-2.5, 0.0, 2.5)                   # deterministic weave; seed can shift it
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player at the start: auto-runs forward, feeds a distance score HUD, and carries
    #    a sound cue so an obstacle hit beeps (killzone SendMessages "PlayCue" to it)
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "runner"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "sound"}})

    # 3) a weaving lane of killzone obstacles ahead (each snaps the player to start on touch)
    for i in range(n):
        oz = (i + 1) * gap
        ox = lanes[i % len(lanes)]
        steps.append({"tool": "unity_create_primitive",
                      "kwargs": {"type": "Cube", "name": f"Obstacle_{i}", "position_y": 0.5,
                                 "position_z": oz, "position_x": ox}})
        steps.append({"script_behaviour": {"object": f"Obstacle_{i}", "behaviour": "killzone"}})

    # 4) a hidden GameManager with a title/start screen: the run begins paused on the
    #    title and starts on Space (title pauses in Start; position is irrelevant for it)
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "title"}})

    return {
        "ok": True,
        "game": "runner",
        "summary": f"Runner: ground + auto-running player (distance score + hit sound) + {n} weaving killzone obstacles + title screen ({len(steps)} steps).",
        "obstacle_count": n,
        "steps": steps,
    }


def plan_tower_defense_game(enemy_count: int = 6, arena_size: float = 24.0) -> dict[str, Any]:
    """Plan a tower-defense -- the 10th game type, all from existing building blocks.

    The twist that makes the existing combat parts behave like a TD: the enemies'
    target is a stationary BASE (tagged Player, so the existing enemy AI -- which
    FindWithTag("Player") -- marches to it) carrying `health`; when the base falls it
    SendMessages "PlayerDied" and the game is LOST. Defending it: a fixed line of
    `ranged` towers (they already auto-target the nearest "Enemy") plus a mobile hero
    (the `player` controller, so the scene has a controllable avatar and assesses as
    playable) who is deliberately NOT tagged Player, so the enemies ignore the hero
    and head for the base. WIN when every enemy is cleared (gameover). Reuses
    health/player/attack/score/ranged/enemy/reward/title/gameover/sound -- no new
    behaviour. Same step schema; the seed jitters the tower line and enemy wave.
    """
    n = max(1, min(int(enemy_count), 30))
    towers = max(2, (n + 1) // 2)
    size = max(8.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) the Base the enemies march to: tagged Player (so the enemy AI targets it) +
    #    health -> when it falls it SendMessages "PlayerDied" and the game is LOST
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Base", "position_y": 0.5, "position_z": -size / 2.0}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Base", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Base", "behaviour": "health"}})

    # 3) a mobile defender hero: WASD + a melee attack (hits "Enemy") + a score HUD.
    #    Carries the player controller (so the scene has a controllable avatar and
    #    assesses playable); NOT tagged Player, so the enemies head for the Base.
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Hero", "position_y": 0.5, "position_z": -size / 2.0 + 3.0}})
    steps.append({"script_behaviour": {"object": "Hero", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Hero", "behaviour": "attack"}})
    steps.append({"script_behaviour": {"object": "Hero", "behaviour": "score"}})

    # 4) defensive towers: a line of stationary pillars with a `ranged` auto-attack
    #    (each already locks the nearest "Enemy" in range and damages it)
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cylinder",
            "count": towers,
            "pattern": "line",
            "spacing": max(3.0, size / float(towers)),
            "name_prefix": "Tower",
        },
    })
    for i in range(towers):
        steps.append({"script_behaviour": {"object": f"Tower_{i}", "behaviour": "ranged"}})

    # 5) the enemy wave: cubes tagged Enemy that march to the Base and can be killed
    #    (enemy AI + reward = their HP, destroyed on death so WIN can trigger)
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "grid",
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Enemy",
        },
    })
    for i in range(n):
        steps.append({"tool": "unity_set_tag", "kwargs": {"name": f"Enemy_{i}", "tag": "Enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "reward"}})

    # 6) GameManager bookend: title start screen + gameover (WIN clear enemies / LOSE
    #    base falls) + a sound cue
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "title"}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "gameover"}})
    steps.append({"script_behaviour": {"object": "GameManager", "behaviour": "sound"}})

    return {
        "ok": True,
        "game": "tower_defense",
        "summary": f"Tower Defense: ground + a Base (enemies' target, lose if it falls) + a mobile hero + {towers} ranged towers + {n} marching enemies + title/win-lose/sound ({len(steps)} steps).",
        "enemy_count": n,
        "tower_count": towers,
        "steps": steps,
    }


def plan_time_survival_game(enemy_count: int = 5, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan an outlast-the-clock survival -- the 11th type, showing the new `timer`
    mechanic. Distinct from `survival` (which never ends): here the win is TIME.

    An armed player (player + health + attack + score) faces N enemies (enemy AI +
    reward, tag Enemy). The hidden GameManager runs title + gameover + sound + a
    `timer`: when the countdown ends the timer SendMessages "Survived" and gameover
    declares a WIN -- you outlasted the clock. LOSE if the player dies first
    (health Die -> PlayerDied). Clearing every enemy early still wins (gameover's
    enemy-clear path), so both "survive" and "win the fight" lead to victory. Same
    step schema; the seed jitters the enemy ring.
    """
    n = max(1, min(int(enemy_count), 30))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) the armed player: movement + health (death -> lose) + attack + score
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    for behaviour in ("player", "health", "attack", "score"):
        steps.append({"script_behaviour": {"object": "Player", "behaviour": behaviour}})

    # 3) enemies: a ring tagged Enemy, each chasing+attacking the player, killable
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(3.0, size / float(n)),
            "name_prefix": "Enemy",
        },
    })
    for i in range(n):
        steps.append({"tool": "unity_set_tag", "kwargs": {"name": f"Enemy_{i}", "tag": "Enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "reward"}})

    # 4) GameManager: title + gameover + sound + a timer. WIN when the timer ends
    #    (Survived) OR all enemies fall; LOSE when the player dies (PlayerDied).
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    for behaviour in ("title", "gameover", "sound", "timer"):
        steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    return {
        "ok": True,
        "game": "time_survival",
        "summary": f"Time Survival: ground + armed player + {n} enemies + a countdown -- outlast the clock to WIN, die to LOSE ({len(steps)} steps).",
        "enemy_count": n,
        "steps": steps,
    }


def plan_stealth_game(guard_count: int = 4, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a stealth game -- the 12th type, and the first won by AVOIDING combat.

    Slip past N patrolling guards (each `patrol` movement + a `detector` line of sight)
    and reach the goal at the far end. A detector SendMessages "PlayerDied" to the
    GameManager if it sees you (caught -> LOSE); reaching the goal SendMessages
    "ReachedGoal" (-> WIN). The guards are deliberately NOT tagged Enemy, so gameover's
    clear-all-enemies WIN never fires -- the only way to win is to reach the exit. Same
    step schema; the seed jitters the guard placement.
    """
    n = max(1, min(int(guard_count), 30))
    size = max(8.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player at the near end
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5, "position_z": -size / 2.0}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    # 3) the exit to slip through to (reaching it -> WIN via gameover.ReachedGoal)
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    # 4) patrolling guards with a line-of-sight detector, NOT tagged Enemy (so clearing
    #    them is neither possible nor a win -- you must avoid them, not fight them)
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Capsule",
            "count": n,
            "pattern": "scatter",
            "spacing": max(3.0, size / float(n)),
            "name_prefix": "Guard",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Guard_{i}", "behaviour": "patrol"}})
        steps.append({"script_behaviour": {"object": f"Guard_{i}", "behaviour": "detector"}})

    # 5) GameManager: title + gameover (WIN on ReachedGoal, LOSE on PlayerDied) + sound
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    for behaviour in ("title", "gameover", "sound"):
        steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    return {
        "ok": True,
        "game": "stealth",
        "summary": f"Stealth: ground + player + a goal exit + {n} patrolling guards (line-of-sight) -- reach the exit unseen to WIN, get spotted to LOSE ({len(steps)} steps).",
        "guard_count": n,
        "steps": steps,
    }


def plan_puzzle_game(crate_count: int = 3, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a sokoban puzzle -- the 13th type, and the first with a PUSH mechanic and no
    combat/timer. Push N crates onto N targets; solve them all to WIN.

    The player (a normal WASD controller) shoves crates by walking into them: each crate
    has the `pushable` behaviour (slides away from the player). N flat `Target_*` markers
    sit on the floor; the hidden GameManager runs `puzzle` (a name-based win manager that
    wins once every target has a crate on it -- no custom Unity tags, no hard type refs)
    plus title + sound. The arena is open (no walls), so every crate can reach every
    target and the puzzle is always solvable. Same step schema; the seed jitters layout.
    """
    n = max(1, min(int(crate_count), 20))
    size = max(8.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player (WASD) -- pushes crates by walking into them
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})

    # 3) N pushable crates (named Crate_* so the puzzle manager scores them)
    steps.append({"tool": "unity_place_primitives", "kwargs": {
        "type": "Cube", "count": n, "pattern": "scatter",
        "spacing": max(2.5, size / float(n)), "name_prefix": "Crate"}})
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Crate_{i}", "behaviour": "pushable"}})

    # 4) N target markers in a ring (named Target_* -- plain, no script needed)
    steps.append({"tool": "unity_place_primitives", "kwargs": {
        "type": "Cylinder", "count": n, "pattern": "circle",
        "spacing": max(3.0, size / float(n)), "name_prefix": "Target"}})

    # 5) GameManager: the puzzle win manager (all crates on targets) + title + sound
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    for behaviour in ("puzzle", "title", "sound"):
        steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    return {
        "ok": True,
        "game": "puzzle",
        "summary": f"Puzzle (sokoban): ground + player + {n} pushable crates + {n} targets -- push every crate onto a target to solve ({len(steps)} steps).",
        "crate_count": n,
        "steps": steps,
    }


def plan_hold_game(enemy_count: int = 4, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a king-of-the-hill -- the 14th type, won by HOLDING a position (not fighting,
    not reaching, not avoiding). A new mechanic: stand your ground under pressure.

    The player has movement + `health` but NO attack -- you can't fight the N enemies
    (enemy AI + reward, tag Enemy) that chase and try to shove you out. A central
    `holdzone` fills a meter while you stay inside it; full -> it SendMessages "Survived"
    to the GameManager (reusing gameover's WIN hook). LOSE if the enemies kill you
    (health Die -> PlayerDied). Since the player can't attack, clearing enemies is not a
    win path -- holding the zone is the only way to win. Same step schema; the seed
    jitters the enemy ring.
    """
    n = max(1, min(int(enemy_count), 30))
    size = max(8.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player: movement + health, but NO attack -- you hold, you don't fight
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "health"}})

    # 3) the hold zone at the centre -- stand in it to fill the meter and WIN
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cylinder", "name": "HoldZone", "position_y": 0.1}})
    steps.append({"script_behaviour": {"object": "HoldZone", "behaviour": "holdzone"}})

    # 4) enemies that chase + attack to push you off the zone (you can't kill them)
    steps.append({"tool": "unity_place_primitives", "kwargs": {
        "type": "Cube", "count": n, "pattern": "circle",
        "spacing": max(3.0, size / float(n)), "name_prefix": "Enemy"}})
    for i in range(n):
        steps.append({"tool": "unity_set_tag", "kwargs": {"name": f"Enemy_{i}", "tag": "Enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "reward"}})

    # 5) GameManager: title + gameover (WIN on Survived from the zone, LOSE on PlayerDied) + sound
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    for behaviour in ("title", "gameover", "sound"):
        steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    return {
        "ok": True,
        "game": "hold",
        "summary": f"Hold (king of the hill): ground + player (no attack) + a central hold zone + {n} enemies -- hold the zone to WIN, die to LOSE ({len(steps)} steps).",
        "enemy_count": n,
        "steps": steps,
    }


def plan_escort_game(enemy_count: int = 4, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan an escort / VIP mission -- the 15th type, and the first won by GUIDING a
    moving NPC to safety. A new mechanic: protect a thing that ISN'T you.

    The Escort is a VIP tagged Player (so the existing enemy AI -- which targets
    FindWithTag("Player") -- marches at the thing you protect, the tower-defense trick
    but with a MOVING base). It walks itself from the near end to the Goal at the far
    end (the new `escort` behaviour: MoveTowards a named goal, deterministic) and carries
    `health`, so if the enemies destroy it the game is LOST (health Die -> PlayerDied).
    You play a separate Hero bodyguard -- the `player` controller + a melee `attack` +
    score, NOT tagged Player -- who clears the N enemies (enemy AI + reward, tag Enemy)
    before they kill the VIP. WIN when the escort reaches the goal (its arrival
    SendMessages ReachedGoal, and the goal zone fires the same for the Player-tagged VIP)
    OR when every enemy is cleared (gameover). Same step schema; the seed jitters the
    enemy ring.
    """
    n = max(1, min(int(enemy_count), 30))
    size = max(8.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) the Escort VIP at the near end: tagged Player (enemies march at IT), walks to the
    #    goal (escort), killable (health -> Die signals PlayerDied = LOSE)
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Capsule", "name": "Escort", "position_y": 0.5, "position_z": -size / 2.0}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Escort", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Escort", "behaviour": "escort"}})
    steps.append({"script_behaviour": {"object": "Escort", "behaviour": "health"}})

    # 3) the goal the VIP walks to (its arrival -> WIN; the goal zone also fires it for
    #    the Player-tagged escort, so the win is doubly robust)
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    # 4) the Hero bodyguard: WASD + a melee attack (hits Enemy) + score. NOT tagged Player,
    #    so the enemies ignore the hero and head for the VIP (the tower-defense hero trick).
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Hero", "position_y": 0.5, "position_z": -size / 2.0 + 3.0}})
    steps.append({"script_behaviour": {"object": "Hero", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Hero", "behaviour": "attack"}})
    steps.append({"script_behaviour": {"object": "Hero", "behaviour": "score"}})

    # 5) enemies between the VIP and the goal: chase the VIP, killable by the hero
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(3.0, size / float(n)),
            "name_prefix": "Enemy",
        },
    })
    for i in range(n):
        steps.append({"tool": "unity_set_tag", "kwargs": {"name": f"Enemy_{i}", "tag": "Enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "enemy"}})
        steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "reward"}})

    # 6) GameManager: title + gameover (WIN on ReachedGoal/clear, LOSE on PlayerDied) + sound
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    for behaviour in ("title", "gameover", "sound"):
        steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    return {
        "ok": True,
        "game": "escort",
        "summary": f"Escort: ground + a VIP (walks to the goal, lose if it falls) + a Hero bodyguard + {n} enemies (chase the VIP) + a goal + title/win-lose/sound ({len(steps)} steps).",
        "enemy_count": n,
        "steps": steps,
    }


def plan_boss_game(boss_count: int = 1, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a boss fight -- the 16th type, and the first sustained single-target DUEL.

    Unlike `arena`/`horde` (a swarm of weak enemies), this is one tough foe: a `boss`
    (the new behaviour, AutopilotBoss -- a single high-HP enemy that chases + melee-attacks
    the player, draws a boss HP bar, and on death grants big XP + destroys itself so
    gameover's clear-all-enemies WIN fires). The player is fully armed (movement + health +
    a melee `attack` + a `ranged` weapon so you can chip the boss at distance + score + xp).
    WIN by defeating the boss; LOSE if it kills you (health Die -> PlayerDied). `boss_count`
    is the number of bosses (default 1, a clean duel; >1 is a boss rush), tagged Enemy and
    cleared to win. Same step schema; the seed jitters the boss placement.
    """
    n = max(1, min(int(boss_count), 10))
    size = max(8.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) the armed player, off to one side: movement + health + melee + ranged + score + xp
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5, "position_z": -size / 3.0}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    for behaviour in ("player", "health", "attack", "ranged", "score", "xp"):
        steps.append({"script_behaviour": {"object": "Player", "behaviour": behaviour}})

    # 3) the boss(es): high-HP foes tagged Enemy, each running the boss behaviour. Placed
    #    via place_primitives so the seed can jitter them (and a boss rush rings the arena).
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Cube",
            "count": n,
            "pattern": "circle",
            "spacing": max(4.0, size / float(n)),
            "name_prefix": "Boss",
        },
    })
    for i in range(n):
        steps.append({"tool": "unity_set_tag", "kwargs": {"name": f"Boss_{i}", "tag": "Enemy"}})
        steps.append({"script_behaviour": {"object": f"Boss_{i}", "behaviour": "boss"}})
        # juice: the boss flashes white each time it is hit (visible because it is high-HP)
        steps.append({"script_behaviour": {"object": f"Boss_{i}", "behaviour": "hitflash"}})

    # 4) GameManager bookend: title + gameover (WIN clears the boss, LOSE on death) + sound
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    for behaviour in ("title", "gameover", "sound"):
        steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    return {
        "ok": True,
        "game": "boss",
        "summary": f"Boss fight: ground + an armed player (health+attack+ranged+xp) vs {n} high-HP boss(es) with an HP bar -- defeat the boss to WIN, die to LOSE ({len(steps)} steps).",
        "boss_count": n,
        "steps": steps,
    }


def plan_collector_race_game(collectible_count: int = 6, arena_size: float = 20.0) -> dict[str, Any]:
    """Plan a collector race -- the 17th type, and the first won by BEATING A DEADLINE.

    Distinct from `collectathon` (collect all, no clock) and `time_survival` (outlast a
    timer to WIN): here the clock is your ENEMY. A WASD player + score HUD races to grab all
    N collectibles before a countdown runs out. The hidden GameManager runs the new
    `collectrace` manager -- it counts the remaining "Collectible_*" by name (decoupled, no
    tags) and SendMessages "ReachedGoal" (reusing gameover's WIN hook) the instant the last
    one is gone, or "PlayerDied" (the LOSE) if the countdown hits zero first -- plus gameover
    + title + sound. Same step schema; the seed jitters the collectible layout.
    """
    n = max(1, min(int(collectible_count), 50))
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player: WASD + a score HUD (collectibles message it +1 each)
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})

    # 3) N collectibles to race for (named Collectible_* so the manager can count them)
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": "Sphere",
            "count": n,
            "pattern": "scatter",
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Collectible",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Collectible_{i}", "behaviour": "collectible"}})

    # 4) GameManager: the collect-race win/lose manager (all collected -> WIN, clock out ->
    #    LOSE) + gameover (the end screen it drives) + title + sound
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
    for behaviour in ("collectrace", "gameover", "title", "sound"):
        steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    return {
        "ok": True,
        "game": "collector_race",
        "summary": f"Collector race: ground + WASD player + score HUD + {n} collectibles + a countdown -- grab them all before time runs out to WIN, run out to LOSE ({len(steps)} steps).",
        "collectible_count": n,
        "steps": steps,
    }


def compose_custom_game(
    player: bool = True,
    enemy: int = 0,
    collectible: int = 0,
    hazard: int = 0,
    goal: bool = False,
    timer: bool = False,
    spawner: int = 0,
    ranged: bool = False,
    guard: int = 0,
    crate: int = 0,
    moving_hazard: int = 0,
    turret: int = 0,
    arena_size: float = 20.0,
    seed: object = None,
) -> dict[str, Any]:
    """Compose a CUSTOM game from a described element mix -- not a fixed blueprint.

    This is the studio's first step from "pick a preset" to "assemble what you asked
    for": given how many of each element the player wants (enemies / collectibles /
    hazards / wave spawners / stealth guards, plus optional goal, timer, and a ranged
    weapon), it builds a valid, playable plan from the same building blocks the
    blueprints use, wiring the sensible couplings:
      - a `player` controller (tagged Player) whenever player=True;
      - if there are enemies, the player gains `health` + `attack` and a hidden
        GameManager runs the win/lose `gameover` (WIN clears enemies, LOSE on death);
      - ranged=True also gives the player a `ranged` weapon (auto-hits the nearest enemy);
      - a `score` HUD when there are collectibles or enemies;
      - collectibles (`collectible`), hazards (`killzone`), moving hazards (`mover` +
        `killzone`, sliding obstacles), wave `spawner`s (raining hazards, survival-style),
        an optional `goal` zone;
      - stealth `guard`s (`patrol` + `detector` line-of-sight, NOT tagged Enemy) that
        make it a 'sneak past them' game: any guard or timer also creates the GameManager,
        and guards imply a goal to reach (auto-added if none) so there IS a way to win;
      - `turret`s (stationary ranged threats that shoot the player, NOT tagged Enemy): the
        player gains `health` and a goal is auto-added -- dodge the fire to reach the exit;
      - sokoban `crate`s (`pushable`) + the same number of `Target_*` markers + a `puzzle`
        win manager on the GameManager (push every crate onto a target to win);
      - if timer=True, the GameManager runs a `timer` -> outlast the clock to WIN
        (Survived), and gets a title + sound for feel.
    Pure + deterministic; same step schema as the blueprints, so it validates, assesses
    and persists exactly like them. Counts are clamped to [0, 30].
    """
    enemy = max(0, min(int(enemy), 30))
    collectible = max(0, min(int(collectible), 30))
    hazard = max(0, min(int(hazard), 30))
    spawner = max(0, min(int(spawner), 20))
    guard = max(0, min(int(guard), 30))
    crate = max(0, min(int(crate), 20))
    moving_hazard = max(0, min(int(moving_hazard), 30))
    turret = max(0, min(int(turret), 30))
    # stealth guards need a goal to slip through to, so there is a real win condition;
    # add one if the user didn't ask for it (mirrors enemy -> health+attack coupling).
    # turrets are the same: an unkillable ranged threat you DODGE to the goal, so they imply one.
    if (guard > 0 or turret > 0) and not goal:
        goal = True
    size = max(6.0, float(arena_size))
    steps: list[dict[str, Any]] = []

    # 1) ground
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # 2) player + the couplings its companions imply
    if player:
        steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_y": 0.5}})
        steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
        player_behaviours = ["player"]
        if enemy > 0:
            player_behaviours += ["health", "attack"]            # so the fight works both ways
        if turret > 0 and "health" not in player_behaviours:
            player_behaviours.append("health")                   # turrets can kill you -> need HP to lose
        if ranged:
            player_behaviours.append("ranged")                   # a long-range weapon too
        if collectible > 0 or enemy > 0:
            player_behaviours.append("score")                    # a HUD to read
        for behaviour in player_behaviours:
            steps.append({"script_behaviour": {"object": "Player", "behaviour": behaviour}})

    # 3) enemies: tagged Enemy, chase+attack the player, killable
    if enemy:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Cube", "count": enemy, "pattern": "circle",
            "spacing": max(3.0, size / float(enemy)), "name_prefix": "Enemy"}})
        for i in range(enemy):
            steps.append({"tool": "unity_set_tag", "kwargs": {"name": f"Enemy_{i}", "tag": "Enemy"}})
            steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "enemy"}})
            steps.append({"script_behaviour": {"object": f"Enemy_{i}", "behaviour": "reward"}})

    # 4) collectibles
    if collectible:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Sphere", "count": collectible, "pattern": "scatter",
            "spacing": max(2.0, size / (2.0 * float(collectible))), "name_prefix": "Collectible"}})
        for i in range(collectible):
            steps.append({"script_behaviour": {"object": f"Collectible_{i}", "behaviour": "collectible"}})

    # 5) hazards: killzone cubes (touch -> respawn the player)
    if hazard:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Cube", "count": hazard, "pattern": "scatter",
            "spacing": max(2.0, size / float(hazard)), "name_prefix": "Hazard"}})
        for i in range(hazard):
            steps.append({"script_behaviour": {"object": f"Hazard_{i}", "behaviour": "killzone"}})

    # 5a2) moving hazards: cubes that SLIDE (mover) and respawn the player on contact
    #      (killzone) -- the dodge game's threat, as a freeform element. Like the static
    #      `hazard` it is a pure obstacle (no win/lose manager, no health coupling).
    if moving_hazard:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Cube", "count": moving_hazard, "pattern": "scatter",
            "spacing": max(2.0, size / float(moving_hazard)), "name_prefix": "MovingHazard"}})
        for i in range(moving_hazard):
            steps.append({"script_behaviour": {"object": f"MovingHazard_{i}", "behaviour": "mover"}})
            steps.append({"script_behaviour": {"object": f"MovingHazard_{i}", "behaviour": "killzone"}})

    # 5b) wave spawners: elevated cubes that rain physics-cube hazards (survival-style)
    if spawner:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Cube", "count": spawner, "pattern": "circle",
            "spacing": max(4.0, size / float(spawner)), "origin_y": 6.0, "name_prefix": "Spawner"}})
        for i in range(spawner):
            steps.append({"script_behaviour": {"object": f"Spawner_{i}", "behaviour": "spawner"}})

    # 5c) stealth guards: patrolling capsules with a line-of-sight `detector` (catch ->
    #     LOSE). NOT tagged Enemy, so they can't be cleared -- you slip past them.
    if guard:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Capsule", "count": guard, "pattern": "scatter",
            "spacing": max(3.0, size / float(guard)), "name_prefix": "Guard"}})
        for i in range(guard):
            steps.append({"script_behaviour": {"object": f"Guard_{i}", "behaviour": "patrol"}})
            steps.append({"script_behaviour": {"object": f"Guard_{i}", "behaviour": "detector"}})

    # 5d) sokoban crates (pushable) + the same number of Target_* markers; the puzzle
    #     manager (added below) wins once every target has a crate on it
    if crate:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Cube", "count": crate, "pattern": "scatter",
            "spacing": max(2.5, size / float(crate)), "name_prefix": "Crate"}})
        for i in range(crate):
            steps.append({"script_behaviour": {"object": f"Crate_{i}", "behaviour": "pushable"}})
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Cylinder", "count": crate, "pattern": "circle",
            "spacing": max(3.0, size / float(crate)), "name_prefix": "Target"}})

    # 5e) stationary turrets: cylinders that shoot the player on a cooldown (`turret`). NOT
    #     tagged Enemy -- you DODGE them to the goal, not kill them (a 'run the gauntlet'
    #     threat). The player got `health` above so their fire can actually defeat you.
    if turret:
        steps.append({"tool": "unity_place_primitives", "kwargs": {
            "type": "Cylinder", "count": turret, "pattern": "scatter",
            "spacing": max(3.0, size / float(turret)), "name_prefix": "Turret"}})
        for i in range(turret):
            steps.append({"script_behaviour": {"object": f"Turret_{i}", "behaviour": "turret"}})

    # 6) an optional goal zone (auto-added above when there are guards or turrets)
    if goal:
        steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_y": 0.5, "position_z": size / 2.0}})
        steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    # 7) a GameManager when there is anything to win or lose. `gameover` lands the
    #    enemy/guard/timer win-lose signals; `puzzle` lands the sokoban win; `timer`
    #    runs the countdown. title + sound give it feel.
    if enemy or timer or guard or crate or turret:
        steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "GameManager", "position_y": -10.0}})
        manager = ["title", "sound"]
        if enemy or timer or guard or turret:
            manager.append("gameover")
        if timer:
            manager.append("timer")                              # outlast the clock -> WIN (Survived)
        if crate:
            manager.append("puzzle")                             # all crates on targets -> WIN
        for behaviour in manager:
            steps.append({"script_behaviour": {"object": "GameManager", "behaviour": behaviour}})

    spec = {"player": bool(player), "enemy": enemy, "collectible": collectible,
            "hazard": hazard, "goal": bool(goal), "timer": bool(timer),
            "spawner": spawner, "ranged": bool(ranged), "guard": guard, "crate": crate,
            "moving_hazard": moving_hazard, "turret": turret}
    parts = []
    if player:
        parts.append("a ranged player" if ranged else "a player")
    for label, c in (("enemies", enemy), ("collectibles", collectible),
                     ("hazards", hazard), ("moving hazards", moving_hazard),
                     ("wave spawners", spawner), ("stealth guards", guard),
                     ("pushable crates", crate), ("turrets", turret)):
        if c:
            parts.append(f"{c} {label}")
    if goal:
        parts.append("a goal")
    if timer:
        parts.append("a countdown")
    plan = {
        "ok": True,
        "game": "custom",
        "summary": f"Custom game: ground + {', '.join(parts) if parts else 'an empty field'} ({len(steps)} steps).",
        "spec": spec,
        "steps": steps,
    }
    # an optional seed jitters the placed-element layout (deterministic), reusing the
    # same machinery the blueprints use; seed=None is a no-op (the plain plan)
    return _apply_seed(plan, "custom",
                       enemy + collectible + hazard + spawner + guard + crate + moving_hazard + turret, seed)


# Decorative (non-gameplay) scripted behaviours that give a scene "juice".
DECOR_BEHAVIOURS = ["bob", "orbit", "rotate", "wander"]


def plan_ambient_decor(
    count: int = 8,
    arena_size: float = 16.0,
    primitive: str = "Sphere",
    pattern: str = "circle",
    behaviours: list[str] | None = None,
) -> dict[str, Any]:
    """Plan a "living scene": place N props and give each a decorative scripted
    behaviour (bob/orbit/rotate/wander, cycled) so the scene breathes. This is
    juice, not a game — there is no player or goal. Same step schema as the game
    blueprints (tool + script_behaviour). Pure + deterministic.

    Unknown/aliased behaviour names are normalized and validated against the
    template registry; anything without a template is dropped (falls back to the
    default decor set if nothing valid remains) so the plan never references a
    phantom behaviour.
    """
    from .gameplay import generate_behaviour_script, normalize_behaviour

    n = max(1, min(int(count), 200))
    size = max(4.0, float(arena_size))
    requested = behaviours if behaviours else DECOR_BEHAVIOURS
    beh = [normalize_behaviour(b) for b in requested]
    beh = [b for b in beh if generate_behaviour_script(b).get("ok")] or list(DECOR_BEHAVIOURS)

    steps: list[dict[str, Any]] = []
    steps.append({
        "tool": "unity_place_primitives",
        "kwargs": {
            "type": primitive,
            "count": n,
            "pattern": pattern,
            "spacing": max(2.0, size / float(n)),
            "name_prefix": "Decor",
        },
    })
    for i in range(n):
        steps.append({"script_behaviour": {"object": f"Decor_{i}", "behaviour": beh[i % len(beh)]}})

    return {
        "ok": True,
        "decor": "ambient",
        "summary": f"Living scene: {n} {primitive}(s) with cycled {'/'.join(beh)} ({len(steps)} steps).",
        "count": n,
        "behaviours": beh,
        "steps": steps,
    }


def group_execution_plan(steps: list[dict[str, Any]]) -> dict[str, Any]:
    """Split a blueprint's steps for efficient execution.

    Returns {geometry, script_behaviours, attachments}. ``script_behaviours`` is
    the DISTINCT behaviour list (so each MonoBehaviour is imported once → a single
    recompile, instead of one per object); ``attachments`` is every (object,
    behaviour) to add as a component after compilation. Geometry runs first so the
    target objects exist before attaching.
    """
    geometry: list[dict[str, Any]] = []
    attachments: list[dict[str, str]] = []
    script_behaviours: list[str] = []
    for step in steps:
        if "tool" in step:
            geometry.append(step)
        elif "script_behaviour" in step:
            sb = step["script_behaviour"]
            attachments.append({"object": sb["object"], "behaviour": sb["behaviour"]})
            if sb["behaviour"] not in script_behaviours:
                script_behaviours.append(sb["behaviour"])
    return {"geometry": geometry, "script_behaviours": script_behaviours, "attachments": attachments}


def plan_maze_game(size: int = 5, arena_size: float = 20.0, seed: object = None) -> dict[str, Any]:
    """Plan a maze game: a deterministic, always-solvable labyrinth you escape.

    Generates a perfect maze (core.maze.generate_maze) and builds it from solid
    wall cubes (each made a static_obstacle), with a WASD+jump player + score HUD
    at the entrance and a goal at the exit. The seed is used at GENERATION time, so
    the same seed always lays out the same maze; it is recorded on the plan so it
    survives save/load. Same step schema as the other blueprints; size is clamped
    to 3..8 to keep the wall count (and object count) reasonable.
    """
    from .maze import generate_maze, maze_wall_positions

    n = max(3, min(int(size), 8))
    cell_size = 2.0
    step = cell_size / 2.0
    mz = generate_maze(seed if seed is not None else "maze-default", n, n)
    walls = maze_wall_positions(mz, cell_size=cell_size, origin=(0.0, 0.0))

    def cell_world(cell: tuple[int, int]) -> tuple[float, float]:
        cx, cy = cell
        return round((2 * cx + 1) * step, 3), round((2 * cy + 1) * step, 3)

    steps: list[dict[str, Any]] = []
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Plane", "name": "Ground"}})

    # solid walls (a Cube already has a collider; static_obstacle makes it explicit)
    for i, (x, z) in enumerate(walls):
        steps.append({"tool": "unity_create_primitive",
                      "kwargs": {"type": "Cube", "name": f"Wall_{i}", "position_x": x, "position_y": 0.5, "position_z": z}})
        steps.append({"tool": "unity_add_gameplay_behaviour",
                      "kwargs": {"object_name": f"Wall_{i}", "behaviour": "static_obstacle"}})

    # player at the entrance, carrying the score HUD
    px, pz = cell_world(mz["entrance"])
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player", "position_x": px, "position_y": 0.5, "position_z": pz}})
    steps.append({"tool": "unity_set_tag", "kwargs": {"name": "Player", "tag": "Player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "player"}})
    steps.append({"script_behaviour": {"object": "Player", "behaviour": "score"}})

    # goal at the exit
    gx, gz = cell_world(mz["exit"])
    steps.append({"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Goal", "position_x": gx, "position_y": 0.5, "position_z": gz}})
    steps.append({"script_behaviour": {"object": "Goal", "behaviour": "goal"}})

    plan: dict[str, Any] = {
        "ok": True,
        "game": "maze",
        "summary": f"Maze: {n}x{n} labyrinth ({len(walls)} walls) + entrance player + exit goal ({len(steps)} steps).",
        "size": n,
        "wall_count": len(walls),
        "steps": steps,
    }
    if seed is not None:
        plan["seed"] = seed
    return plan


# Registry of game blueprints (game_type -> planner). Each planner takes the count
# of its main repeated element and returns {ok, game, summary, steps, ...}.
BLUEPRINTS = {
    "collectathon": plan_collectathon_game,
    "dodge": plan_dodge_game,
    "survival": plan_survival_game,
    "platformer": plan_platformer_game,
    "chase": plan_chase_game,
    "maze": plan_maze_game,
    "arena": plan_arena_game,
    "horde": plan_horde_game,
    "runner": plan_runner_game,
    "tower_defense": plan_tower_defense_game,
    "time_survival": plan_time_survival_game,
    "stealth": plan_stealth_game,
    "puzzle": plan_puzzle_game,
    "hold": plan_hold_game,
    "escort": plan_escort_game,
    "boss": plan_boss_game,
    "collector_race": plan_collector_race_game,
}


def list_blueprints() -> list[str]:
    return sorted(BLUEPRINTS)


_SEED_PATTERNS = ("scatter", "circle", "grid")


def _apply_seed(plan: dict[str, Any], game_type: str, count: int, seed: object) -> dict[str, Any]:
    """Deterministically vary a plan's LAYOUT from a seed, without editing any
    blueprint and without changing what makes it a game.

    For placement steps: a seeded pattern (scatter/circle/grid), a slightly varied
    spacing, and reproducible jitter. For a platformer's staircase: a lateral
    (x-only) shift per platform with the goal kept aligned to the last platform —
    position_y and position_z (the climb) are untouched, so it stays monotone and
    reachable. Object COUNTS and behaviours never change, so every seed stays
    playable and validate-able. None seed is a no-op (identical plain plan).
    """
    if seed is None:
        return plan
    from .procedural import seeded_rng

    rng = seeded_rng(f"{game_type}:{count}:{seed}")
    last_platform_x = 0.0
    for step in plan.get("steps", []):
        tool = step.get("tool")
        if tool == "unity_place_primitives":
            kw = step["kwargs"]
            kw["pattern"] = _SEED_PATTERNS[rng.randint(0, len(_SEED_PATTERNS) - 1)]
            kw["jitter"] = round(rng.uniform(0.5, 2.0), 3)
            kw["spacing"] = round(float(kw.get("spacing", 2.0)) * rng.uniform(0.85, 1.25), 3)
        elif tool == "unity_create_primitive" and str(step["kwargs"].get("name", "")).startswith("Platform_"):
            # lateral shift only — keep position_y / position_z (the climb) intact
            last_platform_x = round(rng.uniform(-2.5, 2.5), 3)
            step["kwargs"]["position_x"] = last_platform_x
        elif tool == "unity_create_primitive" and str(step["kwargs"].get("name", "")).startswith("Obstacle_"):
            # a runner's track: shift each obstacle laterally (within strafe range) so the
            # weave differs per seed; position_z (the forward spacing) is left intact
            step["kwargs"]["position_x"] = round(rng.uniform(-2.5, 2.5), 3)

    # keep a platformer's goal sitting on the highest platform after the x-shift
    for step in plan.get("steps", []):
        if step.get("tool") == "unity_create_primitive" and step["kwargs"].get("name") == "Goal" \
                and any(str(s.get("kwargs", {}).get("name", "")).startswith("Platform_") for s in plan.get("steps", [])):
            step["kwargs"]["position_x"] = last_platform_x

    plan["seed"] = seed
    plan["summary"] = f"{plan.get('summary', '').rstrip('.')} [seed {seed}]."
    return plan


def plan_game(game_type: str = "collectathon", count: int = 5, seed: object = None) -> dict[str, Any]:
    """Dispatch to a blueprint planner by game_type (unknown -> collectathon).

    An optional ``seed`` makes the result reproducibly varied: the same seed
    always yields the same plan; ``seed=None`` (default) is the plain blueprint.
    """
    gt = (game_type or "collectathon").strip().lower()
    planner = BLUEPRINTS.get(gt, plan_collectathon_game)
    if gt == "maze":
        # the maze needs the seed at GENERATION time (not as post-hoc jitter)
        return planner(count, seed=seed)
    return _apply_seed(planner(count), gt, count, seed)


def _difficulty_labels(n: int) -> list[str]:
    """Human difficulty tags for n variations, easy -> hard."""
    presets = {1: ["standard"], 2: ["easy", "hard"], 3: ["easy", "medium", "hard"],
               4: ["easy", "medium", "hard", "extreme"]}
    return presets.get(n, [f"level-{i + 1}" for i in range(n)])


def plan_game_variations(
    game_type: str = "collectathon",
    counts: list[int] | None = None,
    arena_size: float = 20.0,
) -> dict[str, Any]:
    """Generate several variations of ONE game type at different difficulties.

    For each count (sorted ascending so easy->hard is monotonic) it builds the
    plan and attaches a readiness summary from game_qa. Pure + deterministic; no
    bridge, no scene changes. Returns {ok, game_type, count, variations:[{label,
    params, summary, object_count, unique_scripts, playable, warnings}]}.
    """
    from .game_qa import assess_game_readiness  # lazy: game_qa imports this module

    gt = (game_type or "collectathon").strip().lower()
    if gt not in BLUEPRINTS:
        gt = "collectathon"
    planner = BLUEPRINTS[gt]

    raw = counts if counts else [3, 5, 8]
    clean = sorted({max(1, int(c)) for c in raw})         # dedupe + clamp + ascending
    labels = _difficulty_labels(len(clean))

    variations: list[dict[str, Any]] = []
    for label, c in zip(labels, clean):
        plan = planner(c, arena_size)
        report = assess_game_readiness(plan)
        variations.append({
            "label": label,
            "params": {"count": c, "arena_size": float(arena_size)},
            "summary": plan.get("summary", ""),
            "object_count": report["object_count"],
            "unique_scripts": report["unique_scripts"],
            "playable": report["playable"],
            "warnings": report["warnings"],
            "design_notes": report["design_notes"],
        })

    return {"ok": True, "game_type": gt, "count": len(variations), "variations": variations}


def plan_campaign(
    game_type: str = "collectathon",
    levels: int = 3,
    arena_size: float = 20.0,
    seed: object = None,
) -> dict[str, Any]:
    """An ordered, increasing-difficulty CAMPAIGN of one game type: N levels whose
    element count climbs (2, 4, 6, ...), each a FULL playable plan you can build or
    save, with a difficulty label and a readiness check. Unlike plan_game_variations
    (which returns only summaries), a campaign carries each level's plan so the levels
    can be persisted or built. An optional ``seed`` makes each level reproducibly
    varied (a distinct per-level seed derived from it). Pure + deterministic.
    """
    gt = (game_type or "collectathon").strip().lower()
    if gt not in BLUEPRINTS:
        gt = "collectathon"
    n = max(1, min(int(levels), 10))
    labels = _difficulty_labels(n)
    counts = [2 + i * 2 for i in range(n)]                 # 2, 4, 6, ... -- climbing

    from .game_qa import assess_game_readiness             # lazy: game_qa imports this module
    from .game_io import validate_plan                     # lazy: avoid an import cycle
    level_plans: list[dict[str, Any]] = []
    for i, c in enumerate(counts):
        level_seed = f"{seed}-L{i + 1}" if seed is not None else None
        plan = plan_game(gt, c, seed=level_seed)
        report = assess_game_readiness(plan)
        level_plans.append({
            "level": i + 1,
            "label": labels[i] if i < len(labels) else f"level-{i + 1}",
            "count": c,
            "summary": plan.get("summary", ""),
            "valid": bool(validate_plan(plan)["ok"]),     # whitelisted tools, no traversal
            "playable": report["playable"],
            "design_notes": report["design_notes"],
            "plan": plan,
        })

    return {
        "ok": True,
        "kind": "campaign",
        "game_type": gt,
        "level_count": n,
        # a per-campaign self-audit, like studio_health but for this progression
        "all_valid": all(lv["valid"] for lv in level_plans),
        "all_playable": all(lv["playable"] for lv in level_plans),
        "all_coherent": all(not lv["design_notes"] for lv in level_plans),
        "levels": level_plans,
    }
