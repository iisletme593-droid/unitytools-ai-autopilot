"""P7 (cycle 25): blueprint catalog + "build me a game" intent routing.

BLUEPRINTS registry dispatches game_type -> planner; plan_unity_fast_action routes
natural-language game requests to unity_build_simple_game (execute=False, safe).
This closes the loop: a Turkish/English game request -> a full game plan.
"""
from unitytools.core.game_blueprint import BLUEPRINTS, list_blueprints, plan_game
from unitytools.core.game_studio_actions import plan_unity_fast_action


# --- registry --------------------------------------------------------------

def test_blueprints_registry_and_dispatch():
    assert set(list_blueprints()) >= {"collectathon", "dodge"}
    assert plan_game("dodge", 3)["game"] == "dodge"
    assert plan_game("collectathon", 3)["game"] == "collectathon"
    assert plan_game("nonsense", 3)["game"] == "collectathon"   # unknown -> default


# --- intent routing --------------------------------------------------------

def _game_step(prompt):
    plan = plan_unity_fast_action(prompt)
    assert plan["steps"], prompt
    return plan["steps"][0]


def test_dodge_intent():
    step = _game_step("bana bir dodge oyunu kur")
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "dodge"
    assert step["kwargs"]["execute"] is False
    assert step["write"] is False        # safe plan, no scene write


def test_collectathon_intent_with_count():
    step = _game_step("bir toplama oyunu yap 8 toplanabilir")
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "collectathon"
    assert step["kwargs"]["collectible_count"] == 8


def test_generic_build_game():
    step = _game_step("oyun kur")
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "collectathon"


def test_english_game_intent():
    assert _game_step("build me a collectathon game")["kwargs"]["game_type"] == "collectathon"


def test_non_game_prompts_unaffected():
    # forest / scene prompts must NOT be hijacked by the game intent
    assert plan_unity_fast_action("orman kur 40 agac")["steps"][0]["tool"] == "unity_create_optimized_forest_scene"
    assert plan_unity_fast_action("sahneyi listele")["steps"][0]["tool"] == "unity_get_scene_catalog"
