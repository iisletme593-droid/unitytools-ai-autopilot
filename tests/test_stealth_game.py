"""P14 (cycle 81): stealth -- the 12th game type, the first won by AVOIDING combat.

A new `detector` behaviour (line-of-sight -> SendMessage PlayerDied = caught/LOSE), a
new gameover `ReachedGoal()` WIN hook, and the `goal` zone now SendMessages "ReachedGoal"
on entry. plan_stealth_game: player + a goal exit + N patrolling guards (patrol +
detector, NOT tagged Enemy). WIN by reaching the exit, LOSE if a guard sees you.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_stealth_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import assess_game_readiness, critique_design
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the detector behaviour -------------------------------------------------

def test_detector_source():
    s = generate_behaviour_script("detector")
    assert s["ok"] is True and s["class_name"] == "AutopilotDetector"
    src = s["source"]
    assert "sightRange" in src
    assert 'FindWithTag("Player")' in src
    assert 'SendMessage("PlayerDied"' in src and "DontRequireReceiver" in src
    assert "private bool caught" in src                       # fires once


def test_detector_is_deterministic_pure_ascii_balanced():
    src = generate_behaviour_script("detector")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["detector", "dedektor", "gorus", "sight", "algilayici", "nobetci"])
def test_detector_aliases(alias):
    assert normalize_behaviour(alias) == "detector"
    assert generate_behaviour_script(alias)["class_name"] == "AutopilotDetector"


def test_detector_registered():
    assert "detector" in NEEDS_SCRIPT and "detector" in _SCRIPT_TEMPLATES


# --- gameover ReachedGoal hook + goal SendMessage ---------------------------

def test_gameover_gains_a_reached_goal_win_hook():
    src = generate_behaviour_script("gameover")["source"]
    assert "void ReachedGoal()" in src
    body = src.split("void ReachedGoal()")[1].split("}")[0]
    assert "Won = true" in body and "IsOver = true" in body
    # the existing win/lose paths are untouched
    assert "void Survived()" in src and "void PlayerDied()" in src


def test_goal_signals_reached_goal_decoupled():
    src = generate_behaviour_script("goal")["source"]
    assert 'GameObject.Find("GameManager")' in src
    assert 'SendMessage("ReachedGoal"' in src and "DontRequireReceiver" in src
    # the original win flag is still there (other games rely on it)
    assert "won = true" in src and 'CompareTag("Player")' in src


# --- the stealth blueprint --------------------------------------------------

def test_registered_as_twelfth_game():
    assert "stealth" in BLUEPRINTS
    assert plan_game("stealth", 4)["game"] == "stealth"
    assert len(BLUEPRINTS) >= 12


def test_guards_patrol_and_detect_and_are_not_enemies():
    plan = plan_stealth_game(5)
    assert _beh_of(plan, "Guard") == {"patrol", "detector"}
    # guards must NOT be tagged Enemy (else gameover's clear-all WIN would mis-fire)
    enemy_tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                  and s["kwargs"]["tag"] == "Enemy"]
    assert enemy_tags == []


def test_player_goal_and_manager():
    plan = plan_stealth_game(4)
    assert _beh_of(plan, "Player") == {"player"}
    assert _beh_of(plan, "Goal") == {"goal"}            # reach it -> WIN
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}


def test_stealth_is_clean_by_the_design_critique():
    # a goal-win game with a gameover but no enemies/timer must NOT be flagged
    # "can only be lost" -- the critique now recognises the goal as a WIN trigger
    plan = plan_stealth_game(4)
    notes = assess_game_readiness(plan)["design_notes"]
    assert notes == []
    # and the rule itself: gameover + goal (no enemy, no timer) is fine
    assert critique_design({"gameover": 1, "goal": 1, "player": 1}) == []
    # while gameover with NO win trigger at all is still flagged
    assert any("can only be lost" in n for n in critique_design({"gameover": 1, "player": 1}))


@pytest.mark.parametrize("seed", ["a", "b", "42", "sneak"])
def test_valid_and_playable(seed):
    plan = plan_game("stealth", 4, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("stealth", 4, seed="x") == plan_game("stealth", 4, seed="x")
    assert plan_game("stealth", 4, seed="x") != plan_game("stealth", 4, seed="y")
    assert plan_game("stealth", 4, seed=None) == plan_game("stealth", 4)


def test_guard_count_clamped():
    assert plan_stealth_game(0)["guard_count"] == 1
    assert plan_stealth_game(99)["guard_count"] == 30


# --- intent -----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "stealth oyunu kur", "gizlilik oyunu yap", "gizli gec oyunu kur", "sneak game build",
])
def test_stealth_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "stealth", prompt


def test_stealth_does_not_steal_other_intents():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("arena oyunu kur") == "arena"
    assert gt("dodge oyunu yap") == "dodge"
    assert gt("labirent oyunu kur") == "maze"
    assert gt("toplama oyunu yap") == "collectathon"
