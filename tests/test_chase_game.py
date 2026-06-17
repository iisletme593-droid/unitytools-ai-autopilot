"""P7 (cycle 31): chase blueprint — the 5th game type, showcasing `follow`.

Ground + WASD player + score HUD + N enemies that chase the player (follow +
killzone) + a ring of collectibles to grab while escaping + goal. Routed by
intent ("kovalamaca / takip oyunu" / "chase game") to game_type=chase.
"""
import pytest

from unitytools.core.game_blueprint import plan_chase_game, plan_game, BLUEPRINTS, group_execution_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, _BEHAVIOUR_CATEGORIES, _BEHAVIOUR_PURPOSES,
    INTERACTIVE_BEHAVIOURS)


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


def test_chase_groups_to_seven_unique_scripts():
    grouped = group_execution_plan(plan_chase_game(enemy_count=4)["steps"])
    # player + score + follow + killzone + collectible + goal + safezone = 7 unique (one recompile)
    assert set(grouped["script_behaviours"]) == {
        "player", "score", "follow", "killzone", "collectible", "goal", "safezone"}
    # attachments: Player(player)+Player(score) + 4*(follow+killzone) + 4 collectibles + SafeZone + Goal = 16
    assert len(grouped["attachments"]) == 2 + 4 * 2 + 4 + 1 + 1


def test_chase_has_a_central_safe_zone():
    plan = plan_chase_game(enemy_count=4)
    # a SafeZone object running the new safezone behaviour (a retreat the chasers are clamped out of)
    assert any(s.get("script_behaviour") == {"object": "SafeZone", "behaviour": "safezone"}
               for s in plan["steps"])
    # it is its own object, not tagged Enemy -- so it never gets clamped by itself
    safezone_obj = [s for s in plan["steps"] if s.get("tool") == "unity_create_primitive"
                    and s["kwargs"]["name"] == "SafeZone"]
    assert safezone_obj and safezone_obj[0]["kwargs"]["type"] == "Cylinder"


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


# --- cycle 118: the safezone behaviour (chase depth) ------------------------

def test_safezone_source_clamps_chasers_out():
    s = generate_behaviour_script("safezone")
    assert s["ok"] is True and s["class_name"] == "AutopilotSafeZone"
    src = s["source"]
    assert 'StartsWith("Enemy")' in src                        # finds the chasers by name
    assert "LateUpdate" in src                                 # clamps AFTER their movement
    assert "radius" in src                                     # the safe radius


def test_safezone_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("safezone")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["safezone", "guvenli", "siginak", "safehaven"])
def test_safezone_aliases(alias):
    assert normalize_behaviour(alias) == "safezone"


def test_safezone_registered_and_categorized():
    assert "safezone" in NEEDS_SCRIPT and "safezone" in _SCRIPT_TEMPLATES
    assert "safezone" in _BEHAVIOUR_CATEGORIES["world"]         # drift guard
    assert "safezone" in _BEHAVIOUR_PURPOSES                    # glossary drift guard
    assert "safezone" in INTERACTIVE_BEHAVIOURS


def test_safezone_does_not_collide_with_holdzone():
    # "bolge" stays the king-of-the-hill holdzone; the safe-zone uses distinct words
    assert normalize_behaviour("bolge") == "holdzone"


def test_chase_stays_clean_and_seed_independent_with_the_safe_zone():
    # the safe zone is a fixed +1 object -> chase stays valid/playable/coherent + seed-independent
    h = studio_health()
    ch = next(g for g in h["games"] if g["game_type"] == "chase")
    assert ch["valid"] and ch["playable"] and ch["coherent"]
    base = assess_game_readiness(plan_game("chase", 4))["object_count"]
    for seed in ("a", "b", "c"):
        assert assess_game_readiness(plan_game("chase", 4, seed=seed))["object_count"] == base
