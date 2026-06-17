"""P14 (cycle 94): boss fight -- the 16th game type, and the first sustained single-target
DUEL (one high-HP foe, not a swarm).

New `boss` behaviour (AutopilotBoss): a single high-HP enemy that chases + melee-attacks
the player, draws a boss HP bar, and on death grants big XP + destroys itself so
gameover's clear-all-enemies WIN fires. plan_boss_game: an armed player (health + attack
+ ranged + score + xp) vs N bosses (tag Enemy). The design critique was taught that a
`boss` is a foe (like `enemy`), so a boss-only duel is coherent (no false "attack with no
enemies" / "no win trigger" flags).
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_boss_game, plan_game, BLUEPRINTS
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, critique_design, INTERACTIVE_BEHAVIOURS,
    _BEHAVIOUR_CATEGORIES)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the boss behaviour -----------------------------------------------------

def test_boss_source():
    s = generate_behaviour_script("boss")
    assert s["ok"] is True and s["class_name"] == "AutopilotBoss"
    src = s["source"]
    assert "maxHP" in src and "currentHP" in src              # a health pool to whittle down
    assert 'FindWithTag("Player")' in src                     # decoupled
    assert 'SendMessage("TakeDamage"' in src                  # it hits the player
    assert 'SendMessage("AddXP"' in src and "Destroy(gameObject)" in src  # dies -> XP + clears
    assert '"BOSS ' in src                                     # the boss HP bar


def test_boss_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("boss")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["boss", "patron"])
def test_boss_aliases(alias):
    assert normalize_behaviour(alias) == "boss"


def test_boss_registered_and_categorized():
    assert "boss" in NEEDS_SCRIPT and "boss" in _SCRIPT_TEMPLATES
    assert "boss" in INTERACTIVE_BEHAVIOURS                    # a boss is a real threat
    assert "boss" in _BEHAVIOUR_CATEGORIES["combat"]           # drift guard


# --- the refined critique ---------------------------------------------------

def test_critique_treats_a_boss_as_a_foe():
    # a boss-only duel (no small `enemy`) is coherent: attack/ranged have a target and the
    # gameover manager has a WIN trigger (clear the boss)
    assert critique_design({"boss": 1, "health": 1, "attack": 1, "ranged": 1, "gameover": 1}) == []
    # a boss that can hurt the player but the player has no health/attack is still flagged
    assert any("lose condition" in n for n in critique_design({"boss": 1}))
    assert any("one-sided" in n for n in critique_design({"boss": 1, "health": 1}))


def test_critique_unchanged_for_enemy_only_dicts():
    # backward-compat: the `enemy`-based notes still fire exactly as before
    assert any("no enemies to fight" in n for n in critique_design({"attack": 1, "player": 1}))
    assert any("no enemies in range" in n for n in critique_design({"ranged": 2}))


# --- the blueprint ----------------------------------------------------------

def test_registered_as_sixteenth_game():
    assert "boss" in BLUEPRINTS
    assert plan_game("boss", 1)["game"] == "boss"
    assert len(BLUEPRINTS) >= 16


def test_player_is_armed_and_the_boss_is_the_enemy():
    plan = plan_boss_game(1)
    assert _beh_of(plan, "Player") == {"player", "health", "attack", "ranged", "score", "xp"}
    assert _beh_of(plan, "Boss") == {"boss"}
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}
    tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"]
    assert "Player" in tags and tags.count("Enemy") == 1       # one boss, tagged Enemy


def test_boss_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    boss = next(g for g in h["games"] if g["game_type"] == "boss")
    assert boss["valid"] and boss["playable"] and boss["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "boss"])
def test_valid_and_playable(seed):
    plan = plan_game("boss", 2, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert r["design_notes"] == []


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("boss", 2, seed="x") == plan_game("boss", 2, seed="x")
    assert plan_game("boss", 2, seed="x") != plan_game("boss", 2, seed="y")
    assert plan_game("boss", 2, seed=None) == plan_game("boss", 2)


def test_boss_count_clamped():
    assert plan_boss_game(0)["boss_count"] == 1
    assert plan_boss_game(99)["boss_count"] == 10


# --- intent -----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "boss oyunu kur", "patron savasi yap", "boss fight game", "boss arena oyunu kur",
])
def test_boss_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "boss", prompt


def test_boss_does_not_steal_other_intents():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    # "boss arena" must pick boss, but a plain arena must still be arena
    assert gt("arena oyunu kur") == "arena"
    assert gt("dovus oyunu yap") == "arena"
    assert gt("horde oyunu kur") == "horde"
    assert gt("escort oyunu kur") == "escort"
