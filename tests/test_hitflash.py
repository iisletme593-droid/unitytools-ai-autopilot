"""Cycle 101: hitflash -- a feel/juice behaviour. On TakeDamage the renderer flashes, then
fades back. Wired onto bosses (the `boss` type + the arena mini-boss), where the high HP makes
the repeated flash actually visible (one-hit fodder would never show it). Purely cosmetic and
decoupled -- it runs alongside the real damage handler.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_boss_game, plan_arena_game, plan_game
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, INTERACTIVE_BEHAVIOURS, _BEHAVIOUR_CATEGORIES)


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


# --- the behaviour ----------------------------------------------------------

def test_hitflash_source():
    s = generate_behaviour_script("hitflash")
    assert s["ok"] is True and s["class_name"] == "AutopilotHitFlash"
    src = s["source"]
    assert "void TakeDamage(" in src              # responds to the damage message
    assert "Color.Lerp" in src and "flashColor" in src and "baseColor" in src
    assert "GetComponent<Renderer>()" in src      # operates on the renderer


def test_hitflash_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("hitflash")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["hitflash", "parlama", "flash"])
def test_hitflash_aliases(alias):
    assert normalize_behaviour(alias) == "hitflash"


def test_hitflash_registered_and_categorized():
    assert "hitflash" in NEEDS_SCRIPT and "hitflash" in _SCRIPT_TEMPLATES
    assert "hitflash" in _BEHAVIOUR_CATEGORIES["game feel"]
    # it is purely cosmetic: NOT an interactive element (a scene of only flashes is not a game)
    assert "hitflash" not in INTERACTIVE_BEHAVIOURS


# --- wired onto bosses ------------------------------------------------------

def test_boss_type_bosses_flash_on_hit():
    plan = plan_boss_game(2)
    for i in range(2):
        assert _beh_of(plan, f"Boss_{i}") == {"boss", "hitflash"}


def test_arena_mini_boss_flashes_on_hit():
    plan = plan_arena_game(4)
    assert _beh_of(plan, "Boss") == {"boss", "hitflash"}
    # the one-hit swarm does NOT get it (the flash would never be seen on a dying-in-one-hit cube)
    assert "hitflash" not in _beh_of(plan, "Enemy_0")


# --- cosmetic: changes nothing about validity / playability / coherence -----

@pytest.mark.parametrize("game_type", ["boss", "arena"])
def test_boss_games_stay_clean_with_the_juice(game_type):
    h = studio_health()
    g = next(x for x in h["games"] if x["game_type"] == game_type)
    assert g["valid"] and g["playable"] and g["coherent"]
    r = assess_game_readiness(plan_game(game_type, 4))
    assert r["playable"] is True and r["design_notes"] == []


def test_studio_health_still_clean():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"] and h["flagged"] == []
