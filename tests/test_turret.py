"""Cycle 100: the turret composer element -- a stationary RANGED threat that shoots the
player, enabling 'run the gauntlet' custom games (dodge the fire to reach the goal).

New `turret` behaviour (AutopilotTurret): stationary, finds the Player in range and damages
it via SendMessage("TakeDamage") on a cooldown -- the mirror of the player's `ranged`. In the
composer it is NOT tagged Enemy (you can't clear it), so it reuses the guard coupling: the
player gains `health` and a goal is auto-added (a way to win), with a gameover manager.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import compose_custom_game
from unitytools.core.game_qa import (
    assess_game_readiness, compose_health, INTERACTIVE_BEHAVIOURS, _BEHAVIOUR_CATEGORIES)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import parse_custom_spec, plan_unity_fast_action, build_composer_report


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


# --- the behaviour ----------------------------------------------------------

def test_turret_source():
    s = generate_behaviour_script("turret")
    assert s["ok"] is True and s["class_name"] == "AutopilotTurret"
    src = s["source"]
    assert 'FindWithTag(targetTag)' in src and 'targetTag = "Player"' in src   # shoots the player
    assert 'SendMessage("TakeDamage"' in src                                   # decoupled damage
    assert "cooldown" in src and "range" in src


def test_turret_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("turret")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["turret", "taret"])
def test_turret_aliases(alias):
    assert normalize_behaviour(alias) == "turret"


def test_turret_registered_and_categorized():
    assert "turret" in NEEDS_SCRIPT and "turret" in _SCRIPT_TEMPLATES
    assert "turret" in INTERACTIVE_BEHAVIOURS
    assert "turret" in _BEHAVIOUR_CATEGORIES["combat"]


# --- the composer coupling --------------------------------------------------

def test_turret_pulls_in_health_a_goal_and_a_manager():
    plan = compose_custom_game(player=True, turret=4)
    # the player can be killed by turret fire (health), but does NOT get an attack
    assert _beh_of(plan, "Player") == {"player", "health"}
    # a goal is auto-added (the way to win) + a gameover manager (the way to lose)
    assert _beh_of(plan, "Goal") == {"goal"}
    assert "gameover" in _beh_of(plan, "GameManager")
    # the turrets run the turret behaviour and are NOT tagged Enemy (you dodge, not kill)
    assert _beh_of(plan, "Turret_0") == {"turret"}
    enemy_tags = [s for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                  and s["kwargs"]["tag"] == "Enemy"]
    assert enemy_tags == []
    assert plan["spec"]["turret"] == 4


def test_turret_game_is_valid_playable_coherent():
    plan = compose_custom_game(player=True, turret=5)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True and r["has_goal"] is True
    assert r["design_notes"] == []          # goal-win + health-lose with a manager is coherent


def test_turret_count_clamped_and_deterministic():
    assert compose_custom_game(turret=99)["spec"]["turret"] == 30
    a = compose_custom_game(turret=5, seed="t")
    assert a == compose_custom_game(turret=5, seed="t")
    assert a != compose_custom_game(turret=5, seed="u")
    assert compose_custom_game(turret=5, seed=None) == compose_custom_game(turret=5)


def test_turret_with_enemies_keeps_attack_and_stays_coherent():
    # turret + enemies: the player keeps attack (for the enemies), still has health, coherent
    plan = compose_custom_game(player=True, enemy=3, turret=2)
    assert {"health", "attack"} <= _beh_of(plan, "Player")
    assert assess_game_readiness(plan)["design_notes"] == []


# --- the self-audit + parser + report ---------------------------------------

def test_compose_health_audits_turret_clean():
    h = compose_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"] and h["flagged"] == []
    assert any(c["spec"].get("turret") for c in h["cases"])


@pytest.mark.parametrize("text,count", [
    ("ozel oyun 3 taret", 3),
    ("custom game with two turrets", 2),
    ("ozel oyun taret olsun", 1),
])
def test_turret_parsing(text, count):
    assert parse_custom_spec(text)["turret"] == count


def test_composer_report_lists_turret():
    rep = build_composer_report()
    assert "**turret**" in rep and "taret" in rep


def test_turret_routes_keywordless_to_composer_without_stealing_tower_defense():
    def route(p):
        s = plan_unity_fast_action(p)["steps"][0]
        return (s["tool"], s["kwargs"].get("game_type"), s["kwargs"].get("turret"))
    assert route("3 taret olan oyun yap")[0] == "unity_compose_game"
    assert route("3 taret olan oyun yap")[2] == 3
    # the tower-defense PRESET is NOT stolen by the turret word
    assert route("kule savunma yap")[:2] == ("unity_build_simple_game", "tower_defense")
    assert route("tower defense oyunu kur")[:2] == ("unity_build_simple_game", "tower_defense")
