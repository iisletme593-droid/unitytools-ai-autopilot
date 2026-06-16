"""P14 (cycle 75): the freeform game composer -- from "pick a preset" to "assemble
what you described". The biggest step toward real autonomy.

compose_custom_game(player, enemy, collectible, hazard, goal, timer) assembles a valid,
playable plan from the same building blocks the blueprints use, wiring the sensible
couplings (enemies -> player health+attack + a win/lose manager; collectibles/enemies
-> a score HUD; timer -> outlast-the-clock win). parse_custom_spec turns a freeform
description into those kwargs; the `unity_compose_game` tool + an "ozel/custom oyun"
intent route it -- gated so it never steals a preset blueprint.
"""
import pytest

from unitytools.core.game_blueprint import compose_custom_game
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import parse_custom_spec, plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools
import unitytools.tools  # noqa: F401 - register tools


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


# --- the composer -----------------------------------------------------------

def test_compose_wires_combat_couplings_for_enemies():
    plan = compose_custom_game(player=True, enemy=5)
    # enemies imply the player can fight and be hurt, and a win/lose manager exists
    assert {"player", "health", "attack", "score"} <= _beh_of(plan, "Player")
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}
    tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"].startswith("Enemy")]
    assert tags == ["Enemy"] * 5


def test_compose_collectibles_add_a_score_hud():
    plan = compose_custom_game(player=True, collectible=4)
    assert "score" in _beh_of(plan, "Player")
    coll = [s["script_behaviour"]["object"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("behaviour") == "collectible"]
    assert coll == [f"Collectible_{i}" for i in range(4)]


def test_compose_timer_adds_an_outlast_manager():
    plan = compose_custom_game(player=True, timer=True)
    # even with no enemies a timer creates the manager (outlast-the-clock win)
    assert "timer" in _beh_of(plan, "GameManager")
    assert "gameover" in _beh_of(plan, "GameManager")


def test_compose_hazards_and_goal():
    plan = compose_custom_game(player=True, hazard=3, goal=True)
    haz = [s["script_behaviour"]["object"] for s in plan["steps"]
           if s.get("script_behaviour", {}).get("behaviour") == "killzone"]
    assert haz == [f"Hazard_{i}" for i in range(3)]
    assert _beh_of(plan, "Goal") == {"goal"}


def test_compose_is_valid_playable_deterministic():
    plan = compose_custom_game(player=True, enemy=4, collectible=2, hazard=1, timer=True, goal=True)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert compose_custom_game(player=True, enemy=4, collectible=2, hazard=1, timer=True, goal=True) == plan


def test_compose_clamps_counts_and_records_spec():
    plan = compose_custom_game(player=True, enemy=99, collectible=-3)
    assert plan["spec"]["enemy"] == 30 and plan["spec"]["collectible"] == 0
    assert plan["game"] == "custom"


def test_compose_player_only_is_an_honest_sandbox():
    # exactly what was asked: a player and nothing to do -> assessed not playable (honest)
    plan = compose_custom_game(player=True)
    assert validate_plan(plan)["ok"] is True
    assert assess_game_readiness(plan)["playable"] is False


# --- the NL spec parser -----------------------------------------------------

def test_parse_counts_and_flags():
    spec = parse_custom_spec("ozel oyun: 5 dusman 3 toplanabilir ve bir sayac olsun")
    assert spec == {"player": True, "enemy": 5, "collectible": 3, "hazard": 0,
                    "goal": False, "timer": True}


def test_parse_number_words_and_goal():
    spec = parse_custom_spec("custom game with two enemies and a goal")
    assert spec["enemy"] == 2 and spec["goal"] is True and spec["timer"] is False


def test_parse_bare_word_is_one():
    spec = parse_custom_spec("ozel oyun dusman ve engel olsun")
    assert spec["enemy"] == 1 and spec["hazard"] == 1


# --- the tool + intent ------------------------------------------------------

def test_compose_tool_registered_and_pure():
    tool = {t.name: t for t in get_all_tools()}.get("unity_compose_game")
    assert tool is not None
    out = tool.fn(enemy=3, collectible=2)
    assert out["ok"] is True and out["dry_run"] is True
    assert out["assessment"]["playable"] is True


@pytest.mark.parametrize("prompt", [
    "ozel oyun kur 5 dusman 3 toplanabilir",
    "custom game yap 4 dusman",
    "kendi oyunu kur bir sayac ve 2 dusman",
    "karisik oyun: 6 engel",
])
def test_compose_intent_routes(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_compose_game", prompt


def test_compose_intent_carries_the_parsed_spec():
    kw = plan_unity_fast_action("ozel oyun kur 5 dusman 3 toplanabilir ve sayac")["steps"][0]["kwargs"]
    assert kw["enemy"] == 5 and kw["collectible"] == 3 and kw["timer"] is True
    assert kw["execute"] is False


def test_compose_intent_does_not_steal_presets():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    # presets with element counts must still route to the preset builder, not the composer
    assert tool("toplama oyunu yap") == "unity_build_simple_game" and gt("toplama oyunu yap") == "collectathon"
    assert gt("arena oyunu kur 6 dusman") == "arena"
    assert gt("kule savunma yap") == "tower_defense"
    assert gt("dodge oyunu yap") == "dodge"
