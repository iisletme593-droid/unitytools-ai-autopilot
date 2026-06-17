"""P7 (cycle 26): survival blueprint — a third game type, built on the spawner.

Ground + WASD player + M elevated spawners raining hazards. Same building blocks,
a new game; routed by intent ("sağ kalma oyunu") to game_type=survival.
"""
from unitytools.core.game_blueprint import plan_survival_game, plan_game, BLUEPRINTS, group_execution_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def test_survival_plan_structure():
    plan = plan_survival_game(spawner_count=3)
    assert plan["ok"] is True and plan["game"] == "survival"
    assert plan["steps"][0]["kwargs"]["name"] == "Ground"
    # player tagged + controller
    tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"]
    assert tags and tags[0]["kwargs"] == {"name": "Player", "tag": "Player"}
    # M spawners, each with the spawner behaviour
    spawner_targets = [s["script_behaviour"]["object"] for s in plan["steps"]
                       if "script_behaviour" in s and s["script_behaviour"]["behaviour"] == "spawner"]
    assert spawner_targets == [f"Spawner_{i}" for i in range(3)]
    # spawners are elevated so hazards fall
    place = [s for s in plan["steps"] if s.get("tool") == "unity_place_primitives"][0]
    assert place["kwargs"]["origin_y"] == 6.0


def test_spawner_count_clamped():
    assert plan_survival_game(spawner_count=0)["spawner_count"] == 1
    assert plan_survival_game(spawner_count=99)["spawner_count"] == 20


def test_registered_in_catalog():
    assert "survival" in BLUEPRINTS
    assert plan_game("survival", 2)["game"] == "survival"


def test_survival_groups_to_its_unique_scripts():
    grouped = group_execution_plan(plan_survival_game(spawner_count=4)["steps"])
    # cycle 108: survival gained a goal + deadly floor hazards + a win/lose manager
    assert set(grouped["script_behaviours"]) == {
        "player", "spawner", "killzone", "goal", "title", "gameover", "sound"}


def test_survival_now_has_a_real_objective_and_threat():
    # cycle 108 depth: survival used to be harmless + unwinnable. Now it has a goal (WIN) and
    # deadly floor hazards (threat), and is coherent + playable + has a win condition.
    from unitytools.core.game_qa import assess_game_readiness, studio_health
    plan = plan_survival_game(spawner_count=3)
    assert plan["hazard_count"] == 3
    # N killzone hazards + a goal + a gameover manager
    haz = [s["script_behaviour"]["object"] for s in plan["steps"]
           if s.get("script_behaviour", {}).get("behaviour") == "killzone"]
    assert haz == [f"Hazard_{i}" for i in range(3)]
    assert any(s.get("script_behaviour") == {"object": "Goal", "behaviour": "goal"} for s in plan["steps"])
    gm = {s["script_behaviour"]["behaviour"] for s in plan["steps"]
          if s.get("script_behaviour", {}).get("object") == "GameManager"}
    assert gm == {"title", "gameover", "sound"}
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_goal"] is True and r["design_notes"] == []
    h = studio_health()
    sv = next(g for g in h["games"] if g["game_type"] == "survival")
    assert sv["valid"] and sv["playable"] and sv["coherent"]


def test_intent_routes_to_survival():
    for prompt in ["bana sag kalma oyunu kur", "hayatta kalma oyunu yap", "build me a survival game"]:
        step = plan_unity_fast_action(prompt)["steps"][0]
        assert step["tool"] == "unity_build_simple_game"
        assert step["kwargs"]["game_type"] == "survival", prompt


def test_other_game_intents_still_work():
    assert plan_unity_fast_action("dodge oyunu kur")["steps"][0]["kwargs"]["game_type"] == "dodge"
    assert plan_unity_fast_action("toplama oyunu yap")["steps"][0]["kwargs"]["game_type"] == "collectathon"
