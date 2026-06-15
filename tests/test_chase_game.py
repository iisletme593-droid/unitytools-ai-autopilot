"""P7 (cycle 31): chase blueprint — the 5th game type, showcasing `follow`.

Ground + WASD player + score HUD + N enemies that chase the player (follow +
killzone) + a ring of collectibles to grab while escaping + goal. Routed by
intent ("kovalamaca / takip oyunu" / "chase game") to game_type=chase.
"""
from unitytools.core.game_blueprint import plan_chase_game, plan_game, BLUEPRINTS, group_execution_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def test_chase_plan_structure():
    plan = plan_chase_game(enemy_count=4)
    assert plan["ok"] is True and plan["game"] == "chase"
    assert plan["steps"][0]["kwargs"]["name"] == "Ground"
    # player tagged + controller + score HUD
    tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"]
    assert tags and tags[0]["kwargs"] == {"name": "Player", "tag": "Player"}
    player_scripts = {s["script_behaviour"]["behaviour"] for s in plan["steps"]
                      if s.get("script_behaviour", {}).get("object") == "Player"}
    assert player_scripts == {"player", "score"}


def test_each_enemy_chases_and_kills():
    """Every enemy must compose follow (chase) + killzone (touch = respawn)."""
    plan = plan_chase_game(enemy_count=5)
    follow_targets = [s["script_behaviour"]["object"] for s in plan["steps"]
                      if s.get("script_behaviour", {}).get("behaviour") == "follow"]
    kill_targets = [s["script_behaviour"]["object"] for s in plan["steps"]
                    if s.get("script_behaviour", {}).get("behaviour") == "killzone"]
    assert follow_targets == [f"Enemy_{i}" for i in range(5)]
    assert kill_targets == [f"Enemy_{i}" for i in range(5)]


def test_chase_has_collectibles_to_grab():
    plan = plan_chase_game(enemy_count=3)
    collectibles = [s["script_behaviour"]["object"] for s in plan["steps"]
                    if s.get("script_behaviour", {}).get("behaviour") == "collectible"]
    assert collectibles == [f"Collectible_{i}" for i in range(3)]
    # and a goal
    assert any(s.get("script_behaviour") == {"object": "Goal", "behaviour": "goal"}
               for s in plan["steps"])


def test_enemy_count_clamped():
    assert plan_chase_game(enemy_count=0)["enemy_count"] == 1
    assert plan_chase_game(enemy_count=99)["enemy_count"] == 30


def test_registered_in_catalog():
    assert "chase" in BLUEPRINTS
    assert plan_game("chase", 2)["game"] == "chase"


def test_chase_groups_to_six_unique_scripts():
    grouped = group_execution_plan(plan_chase_game(enemy_count=4)["steps"])
    # player + score + follow + killzone + collectible + goal = 6 unique (one recompile)
    assert set(grouped["script_behaviours"]) == {"player", "score", "follow", "killzone", "collectible", "goal"}
    # attachments: Player(player)+Player(score) + 4*(follow+killzone) + 4 collectibles + Goal = 15
    assert len(grouped["attachments"]) == 2 + 4 * 2 + 4 + 1


def test_intent_routes_to_chase():
    for prompt in ["bana kovalamaca oyunu kur", "takip oyunu yap", "build me a chase game"]:
        step = plan_unity_fast_action(prompt)["steps"][0]
        assert step["tool"] == "unity_build_simple_game"
        assert step["kwargs"]["game_type"] == "chase", prompt


def test_other_game_intents_still_work():
    assert plan_unity_fast_action("dodge oyunu kur")["steps"][0]["kwargs"]["game_type"] == "dodge"
    assert plan_unity_fast_action("platform oyunu yap")["steps"][0]["kwargs"]["game_type"] == "platformer"
    assert plan_unity_fast_action("sag kalma oyunu yap")["steps"][0]["kwargs"]["game_type"] == "survival"
    assert plan_unity_fast_action("toplama oyunu yap")["steps"][0]["kwargs"]["game_type"] == "collectathon"
