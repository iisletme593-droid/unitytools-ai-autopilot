"""P7 (cycle 28): platformer blueprint — a fourth game type, built on the jump.

Ground + WASD+jump player + N solid platforms climbing like a staircase + a goal
on top. Reuses the existing player controller (Space jump) and the static_obstacle
physics behaviour (no recompile to make a platform solid). Routed by intent
("platform oyunu") to game_type=platformer.
"""
from unitytools.core.game_blueprint import plan_platformer_game, plan_game, BLUEPRINTS, group_execution_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def test_platformer_plan_structure():
    plan = plan_platformer_game(platform_count=5)
    assert plan["ok"] is True and plan["game"] == "platformer"
    assert plan["steps"][0]["kwargs"]["name"] == "Ground"
    # player tagged + controller (jump comes from the player behaviour)
    tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"]
    assert tags and tags[0]["kwargs"] == {"name": "Player", "tag": "Player"}
    assert any(s.get("script_behaviour") == {"object": "Player", "behaviour": "player"}
               for s in plan["steps"])
    # N platforms, each a created cube made solid with static_obstacle
    platforms = [s for s in plan["steps"]
                 if s.get("tool") == "unity_create_primitive"
                 and str(s["kwargs"].get("name", "")).startswith("Platform_")]
    assert [p["kwargs"]["name"] for p in platforms] == [f"Platform_{i}" for i in range(5)]
    solids = [s for s in plan["steps"]
              if s.get("tool") == "unity_add_gameplay_behaviour"
              and s["kwargs"]["behaviour"] == "static_obstacle"]
    assert [s["kwargs"]["object_name"] for s in solids] == [f"Platform_{i}" for i in range(5)]


def test_platforms_climb_like_a_staircase():
    """Each platform must sit strictly higher (and further) than the previous one."""
    plan = plan_platformer_game(platform_count=6)
    platforms = [s["kwargs"] for s in plan["steps"]
                 if s.get("tool") == "unity_create_primitive"
                 and str(s["kwargs"].get("name", "")).startswith("Platform_")]
    ys = [p["position_y"] for p in platforms]
    zs = [p["position_z"] for p in platforms]
    assert ys == sorted(ys) and len(set(ys)) == len(ys), ys   # strictly increasing height
    assert zs == sorted(zs) and len(set(zs)) == len(zs), zs   # strictly increasing depth


def test_goal_sits_above_the_highest_platform():
    plan = plan_platformer_game(platform_count=4)
    platforms = [s["kwargs"] for s in plan["steps"]
                 if s.get("tool") == "unity_create_primitive"
                 and str(s["kwargs"].get("name", "")).startswith("Platform_")]
    goal = [s["kwargs"] for s in plan["steps"]
            if s.get("tool") == "unity_create_primitive" and s["kwargs"].get("name") == "Goal"][0]
    top_y = max(p["position_y"] for p in platforms)
    assert goal["position_y"] > top_y                          # reachable only by climbing
    assert any(s.get("script_behaviour") == {"object": "Goal", "behaviour": "goal"}
               for s in plan["steps"])


def test_platform_count_clamped():
    assert plan_platformer_game(platform_count=0)["platform_count"] == 1
    assert plan_platformer_game(platform_count=99)["platform_count"] == 30


def test_registered_in_catalog():
    assert "platformer" in BLUEPRINTS
    assert plan_game("platformer", 3)["game"] == "platformer"


def test_platformer_groups_to_four_unique_scripts():
    grouped = group_execution_plan(plan_platformer_game(platform_count=4)["steps"])
    # player + goal + the moving-hazard patrol + killzone; platforms are physics (no recompile)
    assert set(grouped["script_behaviours"]) == {"player", "goal", "patrol", "killzone"}
    # the static_obstacle steps live in geometry (no recompile)
    solids = [g for g in grouped["geometry"] if g["tool"] == "unity_add_gameplay_behaviour"]
    assert len(solids) == 4


def test_odd_platforms_carry_a_patrolling_killzone_hazard():
    # cycle 107 depth: every OTHER platform (odd index) gets a moving hazard; the first is safe
    plan = plan_platformer_game(platform_count=5)
    # platforms 1 + 3 are guarded -> 2 hazards
    assert plan["hazard_count"] == 2
    haz = [s["script_behaviour"]["object"] for s in plan["steps"]
           if s.get("script_behaviour", {}).get("behaviour") == "patrol"]
    assert haz == ["Hazard_0", "Hazard_1"]
    # each hazard both patrols (sweeps, stays in play) and kills on touch (respawn)
    assert {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == "Hazard_0"} == {"patrol", "killzone"}
    # the hazards are NOT platforms (the staircase + goal assertions are untouched)
    assert not any(str(s.get("kwargs", {}).get("name", "")).startswith("Hazard_")
                   and s.get("tool") == "unity_add_gameplay_behaviour" for s in plan["steps"])


def test_intent_routes_to_platformer():
    for prompt in ["bana platform oyunu kur", "platformer yap", "ziplama oyunu yap",
                   "build me a platformer", "make a jump game"]:
        step = plan_unity_fast_action(prompt)["steps"][0]
        assert step["tool"] == "unity_build_simple_game"
        assert step["kwargs"]["game_type"] == "platformer", prompt


def test_other_game_intents_still_work():
    assert plan_unity_fast_action("dodge oyunu kur")["steps"][0]["kwargs"]["game_type"] == "dodge"
    assert plan_unity_fast_action("sag kalma oyunu yap")["steps"][0]["kwargs"]["game_type"] == "survival"
    assert plan_unity_fast_action("toplama oyunu yap")["steps"][0]["kwargs"]["game_type"] == "collectathon"
