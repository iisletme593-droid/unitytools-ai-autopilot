"""P14 (cycle 114): key-and-door -- the 20th game type, and the first with a FETCH-THEN-EXIT gate.

New `lockgoal` behaviour (AutopilotLockGoal): a locked exit that counts the remaining "Key_*" by
name and stays LOCKED until none are left, then -- when the player reaches it -- SendMessages
"ReachedGoal" (the WIN, reusing gameover's hook). plan_keydoor_game: a WASD player + score
collects N keys (collectible, named Key_*) and dodges killzone hazards, then reaches the unlocked
Door. Distinct from collectathon (collect AT the goal) and collector_race (a clock): here the keys
UNLOCK a separate exit you must then reach. The critique learns lockgoal is a valid WIN trigger.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import plan_keydoor_game, plan_game, compose_custom_game, BLUEPRINTS
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, critique_design, game_howto_from_plan,
    build_game_howto, _BEHAVIOUR_CATEGORIES, _GAME_EXAMPLES, INTERACTIVE_BEHAVIOURS)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the lockgoal behaviour -------------------------------------------------

def test_lockgoal_source_counts_keys_and_wins_on_reach():
    s = generate_behaviour_script("lockgoal")
    assert s["ok"] is True and s["class_name"] == "AutopilotLockGoal"
    src = s["source"]
    assert 'StartsWith("Key")' in src                          # counts keys by name
    assert 'SendMessage("ReachedGoal"' in src                  # WIN when unlocked + reached
    assert "OnTriggerEnter" in src and 'CompareTag("Player")' in src
    assert "keysLeft" in src                                    # the lock state


def test_lockgoal_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("lockgoal")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["lockgoal", "kilitkapi", "lockeddoor", "kilitlicikis"])
def test_lockgoal_aliases(alias):
    assert normalize_behaviour(alias) == "lockgoal"


def test_lockgoal_registered_and_categorized():
    assert "lockgoal" in NEEDS_SCRIPT and "lockgoal" in _SCRIPT_TEMPLATES
    assert "lockgoal" in _BEHAVIOUR_CATEGORIES["world"]         # drift guard
    assert "lockgoal" in INTERACTIVE_BEHAVIOURS                 # it makes a game playable


# --- the refined critique ---------------------------------------------------

def test_critique_treats_lockgoal_as_a_win_trigger():
    # a gameover manager paired with a lockgoal HAS a win path (unlock + reach the exit), so it
    # must NOT be flagged "can only be lost"
    assert critique_design({"lockgoal": 1, "gameover": 1, "collectible": 3}) == []
    # a bare gameover with no enemies/timer/goal/collectrace/lockgoal is still flagged
    assert any("can only be lost" in n for n in critique_design({"gameover": 1, "player": 1}))


# --- the blueprint ----------------------------------------------------------

def test_registered_as_twentieth_game():
    assert "keydoor" in BLUEPRINTS
    assert plan_game("keydoor", 3)["game"] == "keydoor"
    assert len(BLUEPRINTS) >= 20


def test_layout_is_fetch_keys_then_locked_exit():
    plan = plan_keydoor_game(3)
    assert _beh_of(plan, "Player") == {"player", "score"}
    assert _beh_of(plan, "Key") == {"collectible"}             # keys are collectibles (named Key_*)
    assert _beh_of(plan, "Hazard") == {"killzone"}
    assert _beh_of(plan, "Door") == {"lockgoal"}               # the locked exit
    assert _beh_of(plan, "GameManager") == {"gameover", "title", "sound"}
    n_keys = sum(1 for s in plan["steps"]
                 if s.get("script_behaviour", {}).get("behaviour") == "collectible")
    assert n_keys == 3
    # only the player is tagged -- the keys/hazards are not enemies, so the only win is the exit
    tags = {s["kwargs"].get("tag") for s in plan["steps"] if s.get("tool") == "unity_set_tag"}
    assert tags == {"Player"}


def test_keydoor_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    kd = next(g for g in h["games"] if g["game_type"] == "keydoor")
    assert kd["valid"] and kd["playable"] and kd["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "key"])
def test_valid_and_playable(seed):
    plan = plan_game("keydoor", 3, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True
    assert r["has_goal"] is True                               # the lockgoal counts as the exit
    assert r["design_notes"] == [] and r["warnings"] == []


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("keydoor", 3, seed="x") == plan_game("keydoor", 3, seed="x")
    assert plan_game("keydoor", 3, seed="x") != plan_game("keydoor", 3, seed="y")
    assert plan_game("keydoor", 3, seed=None) == plan_game("keydoor", 3)


def test_key_count_clamped():
    assert plan_keydoor_game(0)["key_count"] == 1
    assert plan_keydoor_game(99)["key_count"] == 40


# --- how-to derivation ------------------------------------------------------

def test_howto_is_about_unlocking_and_reaching_the_exit():
    h = game_howto_from_plan(plan_game("keydoor", 3))
    win = " ".join(h["win"]).lower()
    assert "key" in win and "unlock" in win and "reach it" in win
    assert any("hazard" in t.lower() for t in h["threats"])
    text = build_game_howto("keydoor")
    assert all(ord(c) < 128 for c in text)
    for section in ("## Controls", "## How to win", "## Watch out for", "## How you lose"):
        assert section in text


# --- showcase + intent ------------------------------------------------------

def test_showcase_example_present():
    assert "keydoor" in _GAME_EXAMPLES
    prompt, pitch = _GAME_EXAMPLES["keydoor"]
    assert pitch and all(ord(c) < 128 for c in prompt + pitch)


@pytest.mark.parametrize("prompt", [
    "keydoor oyunu kur", "anahtarli kapi oyunu yap", "kilitli kapi oyunu kur",
    "locked exit game", "key door game",
])
def test_keydoor_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "keydoor", prompt


def test_keydoor_does_not_steal_collectathon_or_the_composer_goal_flag():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    # plain collect intents are untouched
    assert gt("toplama oyunu yap") == "collectathon"
    assert gt("collectathon oyunu kur") == "collectathon"
    # bare "kapi" is the composer's goal flag, NOT a keydoor trigger -> stays composer/collectathon
    s = plan_unity_fast_action("ozel oyun 3 dusman ve kapi")["steps"][0]
    assert s["tool"] == "unity_compose_game" and s["kwargs"]["goal"] is True
