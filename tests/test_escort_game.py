"""P14 (cycle 93): escort / VIP mission -- the 15th game type, won by GUIDING a moving
NPC to safety (protect a thing that isn't you).

New `escort` behaviour (AutopilotEscort): a VIP that walks ITSELF toward a named goal
(MoveTowards, deterministic) and fires a one-time "ReachedGoal" on arrival (reusing
gameover's WIN hook). plan_escort_game uses the tower-defense inversion with a MOVING
base: the Escort is tagged Player (so the enemy AI marches at the thing you protect) +
health (destroy it -> LOSE); a separate, untagged Hero is the controllable bodyguard
(player + attack + score) who clears the enemies. Win by delivering the VIP (or clearing
every enemy); lose if the VIP falls.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_escort_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, _BEHAVIOUR_CATEGORIES)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


def _tags(plan):
    return {s["kwargs"]["name"]: s["kwargs"]["tag"] for s in plan["steps"]
            if s.get("tool") == "unity_set_tag"}


# --- the escort behaviour ---------------------------------------------------

def test_escort_source():
    s = generate_behaviour_script("escort")
    assert s["ok"] is True and s["class_name"] == "AutopilotEscort"
    src = s["source"]
    assert "goalName" in src and "MoveTowards" in src         # walks to a named goal
    assert 'GameObject.Find(goalName)' in src                 # decoupled, by name
    assert 'SendMessage("ReachedGoal"' in src                 # reuses the win hook
    assert "arrived" in src                                   # fires once


def test_escort_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("escort")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["escort", "eskort", "refakat", "vip"])
def test_escort_aliases(alias):
    assert normalize_behaviour(alias) == "escort"


def test_escort_registered_and_categorized():
    assert "escort" in NEEDS_SCRIPT and "escort" in _SCRIPT_TEMPLATES
    # the drift guard requires every class to be categorized; escort lives under "world"
    assert "escort" in _BEHAVIOUR_CATEGORIES["world"]


# --- the blueprint ----------------------------------------------------------

def test_registered_as_fifteenth_game():
    assert "escort" in BLUEPRINTS
    assert plan_game("escort", 4)["game"] == "escort"
    assert len(BLUEPRINTS) >= 15


def test_the_vip_is_the_player_tagged_base_not_the_hero():
    plan = plan_escort_game(4)
    # the VIP walks to the goal and can be killed; the hero fights but is untagged
    assert _beh_of(plan, "Escort") == {"escort", "health"}
    assert _beh_of(plan, "Hero") == {"player", "attack", "score"}
    assert _beh_of(plan, "Goal") == {"goal"}
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}
    tags = _tags(plan)
    # the tower-defense inversion: the thing you protect (the moving VIP) carries the
    # Player tag so the enemies march at IT; the controllable Hero is deliberately untagged
    assert tags["Escort"] == "Player"
    assert "Hero" not in tags
    assert [v for k, v in tags.items() if k.startswith("Enemy")] == ["Enemy"] * 4


def test_escort_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    esc = next(g for g in h["games"] if g["game_type"] == "escort")
    assert esc["valid"] and esc["playable"] and esc["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "vip"])
def test_valid_and_playable(seed):
    plan = plan_game("escort", 4, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert r["has_goal"] is True
    assert r["design_notes"] == []                            # coherent: nothing flagged


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("escort", 4, seed="x") == plan_game("escort", 4, seed="x")
    assert plan_game("escort", 4, seed="x") != plan_game("escort", 4, seed="y")
    assert plan_game("escort", 4, seed=None) == plan_game("escort", 4)


def test_enemy_count_clamped():
    assert plan_escort_game(0)["enemy_count"] == 1
    assert plan_escort_game(99)["enemy_count"] == 30


# --- intent -----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "escort oyunu kur", "refakat oyunu yap", "vip escort game", "eskort gorevi yap",
])
def test_escort_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "escort", prompt


def test_escort_does_not_steal_other_intents():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("arena oyunu kur") == "arena"
    assert gt("hold the zone game") == "hold"
    assert gt("stealth oyunu kur") == "stealth"
    assert gt("toplama oyunu yap") == "collectathon"
    # the guard composer word "koruma" must NOT be stolen by escort's detection: it still
    # routes to the freeform composer (3 guards), not an escort build
    assert plan_unity_fast_action("3 koruma olan oyun yap")["steps"][0]["tool"] == "unity_compose_game"
