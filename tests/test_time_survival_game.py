"""P14 (cycle 74): the `timer` mechanic + time_survival -- the 11th game type.

`timer` (AutopilotTimer) counts a duration down, draws the remaining seconds, and on
zero fires a decoupled SendMessage("Survived"). `gameover` gains a Survived() WIN hook
(mirrors PlayerDied but Won=true), so an outlast-the-clock game is won by surviving.
plan_time_survival_game wires an armed player vs N enemies + a GameManager running
title+gameover+sound+timer: WIN by surviving the countdown (or clearing enemies), LOSE
on death. Distinct from `survival` (which never ends).
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import (
    plan_time_survival_game, plan_game, BLUEPRINTS)
from unitytools.core.game_qa import assess_game_readiness, _BEHAVIOUR_CATEGORIES
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


# --- the timer behaviour ---------------------------------------------------

def test_timer_source():
    s = generate_behaviour_script("timer")
    assert s["ok"] is True and s["class_name"] == "AutopilotTimer"
    src = s["source"]
    assert "public float duration" in src                       # configurable countdown
    assert "remaining -= Time.deltaTime" in src                 # counts down
    assert "GUI.Label" in src and '"Time: "' in src             # HUD
    assert 'SendMessage("Survived"' in src                      # decoupled win signal
    assert "DontRequireReceiver" in src


def test_timer_fires_survived_once():
    src = generate_behaviour_script("timer")["source"]
    assert "private bool fired" in src and "if (fired) return;" in src  # exactly once


def test_timer_is_deterministic_pure_ascii_balanced():
    src = generate_behaviour_script("timer")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime", "System.Random"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["timer", "sure", "zaman", "countdown", "gerisayim", "saat"])
def test_timer_aliases(alias):
    assert normalize_behaviour(alias) == "timer"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotTimer"


def test_timer_does_not_steal_the_score_sayac_alias():
    assert normalize_behaviour("sayac") == "score"              # unchanged
    assert "timer" in NEEDS_SCRIPT and "timer" in _SCRIPT_TEMPLATES


def test_timer_is_categorized_in_the_studio_report():
    # the drift guard would fail if timer were uncategorized; assert it explicitly too
    assert "timer" in _BEHAVIOUR_CATEGORIES["game feel"]


# --- the gameover Survived() WIN hook --------------------------------------

def test_gameover_gains_a_survived_win_hook():
    src = generate_behaviour_script("gameover")["source"]
    assert "void Survived()" in src
    survived = src.split("void Survived()")[1].split("}")[0]
    assert "Won = true" in survived and "IsOver = true" in survived
    # the existing enemy-clear WIN and PlayerDied LOSE are still there
    assert 'FindGameObjectsWithTag("Enemy")' in src and "void PlayerDied()" in src


# --- the time_survival blueprint -------------------------------------------

def test_registered_as_eleventh_game():
    assert "time_survival" in BLUEPRINTS
    assert plan_game("time_survival", 5)["game"] == "time_survival"
    assert len(BLUEPRINTS) >= 11


def test_player_is_armed_and_manager_has_the_timer():
    plan = plan_time_survival_game(5)
    assert _beh_of(plan, "Player") == {"player", "health", "hitflash", "attack", "score"}
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound", "timer"}


def test_enemies_tagged_and_killable():
    plan = plan_time_survival_game(4)
    tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"].startswith("Enemy")]
    assert tags == ["Enemy"] * 4
    assert _beh_of(plan, "Enemy_0") == {"enemy", "reward"}


@pytest.mark.parametrize("seed", ["a", "b", "30", "clock"])
def test_valid_and_playable(seed):
    plan = plan_game("time_survival", 5, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("time_survival", 5, seed="x") == plan_game("time_survival", 5, seed="x")
    assert plan_game("time_survival", 5, seed="x") != plan_game("time_survival", 5, seed="y")
    assert plan_game("time_survival", 5, seed=None) == plan_game("time_survival", 5)


def test_enemy_count_clamped():
    assert plan_time_survival_game(0)["enemy_count"] == 1
    assert plan_time_survival_game(99)["enemy_count"] == 30


# --- intent ----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "zamana karsi oyun kur",
    "sureli hayatta kalma oyunu yap",
    "survive the clock oyunu",
    "time survival kur",
    "gerisayim oyunu yap",
])
def test_time_survival_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "time_survival", prompt


def test_does_not_steal_plain_survival():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("hayatta kalma oyunu kur") == "survival"          # plain survival unchanged
    assert gt("survival oyunu yap") == "survival"
    assert gt("sag kalma oyunu") == "survival"
