"""P14 (cycle 95): collector race -- the 17th game type, and the first won by BEATING A
DEADLINE (the clock is your enemy).

New `collectrace` behaviour (AutopilotCollectRace): a manager that counts the remaining
"Collectible_*" by name and SendMessages "ReachedGoal" (reusing gameover's WIN hook) when
the last one is gone, or "PlayerDied" (the LOSE) if its countdown hits zero first.
plan_collector_race_game: a WASD player + score + N collectibles + the manager. Distinct
from collectathon (no clock) and time_survival (the timer is a WIN). The design critique
learned that a `collectrace` is a valid WIN trigger.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_collector_race_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, critique_design, _BEHAVIOUR_CATEGORIES)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the collectrace behaviour ----------------------------------------------

def test_collectrace_source():
    s = generate_behaviour_script("collectrace")
    assert s["ok"] is True and s["class_name"] == "AutopilotCollectRace"
    src = s["source"]
    assert 'StartsWith("Collectible")' in src                 # counts collectibles by name
    assert 'SendMessage("ReachedGoal"' in src                 # WIN when all collected
    assert 'SendMessage("PlayerDied"' in src                  # LOSE when the clock runs out
    assert "remainingTime" in src and "Time.deltaTime" in src  # the countdown


def test_collectrace_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("collectrace")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["collectrace", "collectorrace", "yaris"])
def test_collectrace_aliases(alias):
    assert normalize_behaviour(alias) == "collectrace"


def test_collectrace_registered_and_categorized():
    assert "collectrace" in NEEDS_SCRIPT and "collectrace" in _SCRIPT_TEMPLATES
    assert "collectrace" in _BEHAVIOUR_CATEGORIES["game feel"]  # drift guard


# --- the refined critique ---------------------------------------------------

def test_critique_treats_collectrace_as_a_win_trigger():
    # a gameover manager paired with a collectrace HAS a win path (collect them all), so it
    # must NOT be flagged "can only be lost"
    assert critique_design({"collectrace": 1, "gameover": 1, "collectible": 5}) == []
    # a bare gameover with no enemies/timer/goal/collectrace is still flagged
    assert any("can only be lost" in n for n in critique_design({"gameover": 1, "player": 1}))


# --- the blueprint ----------------------------------------------------------

def test_registered_as_seventeenth_game():
    assert "collector_race" in BLUEPRINTS
    assert plan_game("collector_race", 6)["game"] == "collector_race"
    assert len(BLUEPRINTS) >= 17


def test_player_collects_and_the_manager_runs_the_race():
    plan = plan_collector_race_game(6)
    assert _beh_of(plan, "Player") == {"player", "score"}
    assert _beh_of(plan, "GameManager") == {"collectrace", "gameover", "title", "sound"}
    # six collectibles, each with the pickup behaviour
    collectibles = _beh_of(plan, "Collectible")
    assert collectibles == {"collectible"}
    n_pickups = sum(1 for s in plan["steps"]
                    if s.get("script_behaviour", {}).get("behaviour") == "collectible")
    assert n_pickups == 6


def test_collector_race_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    cr = next(g for g in h["games"] if g["game_type"] == "collector_race")
    assert cr["valid"] and cr["playable"] and cr["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "race"])
def test_valid_and_playable(seed):
    plan = plan_game("collector_race", 6, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert r["design_notes"] == []


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("collector_race", 6, seed="x") == plan_game("collector_race", 6, seed="x")
    assert plan_game("collector_race", 6, seed="x") != plan_game("collector_race", 6, seed="y")
    assert plan_game("collector_race", 6, seed=None) == plan_game("collector_race", 6)


def test_collectible_count_clamped():
    assert plan_collector_race_game(0)["collectible_count"] == 1
    assert plan_collector_race_game(99)["collectible_count"] == 50


# --- intent -----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "collector race oyunu kur", "toplama yarisi yap", "sureli toplama oyunu", "collection race game",
])
def test_collector_race_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "collector_race", prompt


def test_collector_race_does_not_steal_collectathon_or_time_survival():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    # plain collect / survival intents are untouched (bare "toplama" stays a collectathon)
    assert gt("toplama oyunu yap") == "collectathon"
    assert gt("collectathon oyunu kur") == "collectathon"
    assert gt("sureli hayatta kalma oyunu") == "time_survival"
    assert gt("arena oyunu kur") == "arena"
