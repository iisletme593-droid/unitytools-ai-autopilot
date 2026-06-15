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


def test_survival_groups_to_two_unique_scripts():
    grouped = group_execution_plan(plan_survival_game(spawner_count=4)["steps"])
    assert grouped["script_behaviours"] == ["player", "spawner"]   # 2 unique
    assert len(grouped["attachments"]) == 5                        # player + 4 spawners


def test_intent_routes_to_survival():
    for prompt in ["bana sag kalma oyunu kur", "hayatta kalma oyunu yap", "build me a survival game"]:
        step = plan_unity_fast_action(prompt)["steps"][0]
        assert step["tool"] == "unity_build_simple_game"
        assert step["kwargs"]["game_type"] == "survival", prompt


def test_other_game_intents_still_work():
    assert plan_unity_fast_action("dodge oyunu kur")["steps"][0]["kwargs"]["game_type"] == "dodge"
    assert plan_unity_fast_action("toplama oyunu yap")["steps"][0]["kwargs"]["game_type"] == "collectathon"
