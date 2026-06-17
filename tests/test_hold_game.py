"""P14 (cycle 90): king of the hill -- the 14th game type, won by HOLDING a position.

A new mechanic (not fight / reach / avoid): stand your ground. New `holdzone`
behaviour (AutopilotHoldZone) fills a meter while the Player is inside and SendMessages
"Survived" (reusing gameover's WIN hook) when full. plan_hold_game: a player with
health but NO attack + a central hold zone + N enemies that push you out. Win by
holding; lose by dying. The design critique was refined so a no-attack game with a
holdzone/goal win path is NOT flagged "one-sided".
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_hold_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import (
    assess_game_readiness, INTERACTIVE_BEHAVIOURS, studio_health, critique_design)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the holdzone behaviour -------------------------------------------------

def test_holdzone_source():
    s = generate_behaviour_script("holdzone")
    assert s["ok"] is True and s["class_name"] == "AutopilotHoldZone"
    src = s["source"]
    assert "radius" in src and "holdTime" in src
    assert 'FindWithTag("Player")' in src                  # decoupled
    assert 'SendMessage("Survived"' in src                 # reuses the win hook
    assert '"Hold: "' in src                               # the meter HUD


def test_holdzone_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("holdzone")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["hold", "holdzone", "bolge", "zone", "tepe", "kapma"])
def test_holdzone_aliases(alias):
    assert normalize_behaviour(alias) == "holdzone"


def test_holdzone_registered_and_interactive():
    assert "holdzone" in NEEDS_SCRIPT and "holdzone" in _SCRIPT_TEMPLATES
    assert "holdzone" in INTERACTIVE_BEHAVIOURS


# --- the refined critique ---------------------------------------------------

def test_critique_allows_no_attack_when_there_is_a_hold_or_goal_win():
    # enemies + no attack is FINE when a holdzone or goal gives a non-combat win...
    assert critique_design({"enemy": 4, "health": 1, "holdzone": 1, "gameover": 1}) == []
    assert critique_design({"enemy": 4, "health": 1, "goal": 1, "gameover": 1}) == []
    # ...but still flagged when there is NO way to win without fighting
    assert any("one-sided" in n for n in critique_design({"enemy": 4, "health": 1}))


# --- the blueprint ----------------------------------------------------------

def test_registered_as_fourteenth_game():
    assert "hold" in BLUEPRINTS
    assert plan_game("hold", 4)["game"] == "hold"
    assert len(BLUEPRINTS) >= 14


def test_player_has_no_attack_and_the_zone_is_the_win():
    plan = plan_hold_game(4)
    # the player can move + be hurt (and flash when hit) but CANNOT attack (holding, not fighting)
    assert _beh_of(plan, "Player") == {"player", "health", "hitflash"}
    assert _beh_of(plan, "HoldZone") == {"holdzone"}
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}
    tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"].startswith("Enemy")]
    assert tags == ["Enemy"] * 4


def test_hold_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    hold = next(g for g in h["games"] if g["game_type"] == "hold")
    assert hold["valid"] and hold["playable"] and hold["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "hill"])
def test_valid_and_playable(seed):
    plan = plan_game("hold", 4, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert r["design_notes"] == []


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("hold", 4, seed="x") == plan_game("hold", 4, seed="x")
    assert plan_game("hold", 4, seed="x") != plan_game("hold", 4, seed="y")
    assert plan_game("hold", 4, seed=None) == plan_game("hold", 4)


def test_enemy_count_clamped():
    assert plan_hold_game(0)["enemy_count"] == 1
    assert plan_hold_game(99)["enemy_count"] == 30


# --- intent -----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "king of the hill oyunu kur", "bolge tut oyunu yap", "hold the zone game", "zone control kur",
])
def test_hold_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "hold", prompt


def test_hold_does_not_steal_other_intents():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("arena oyunu kur") == "arena"
    assert gt("puzzle oyunu kur") == "puzzle"
    assert gt("toplama oyunu yap") == "collectathon"
    assert gt("stealth oyunu kur") == "stealth"
