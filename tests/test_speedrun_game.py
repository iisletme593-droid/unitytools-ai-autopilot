"""P14 (cycle 110): speedrun -- the 19th game type, and the first won by BEATING A DEADLINE
TO THE EXIT (a destination race against a LOSING clock).

New `deadline` behaviour (AutopilotDeadline): the mirror of AutopilotTimer -- a countdown that
SendMessages "PlayerDied" (the LOSE) when it hits zero, instead of "Survived" (the WIN). On the
GameManager next to gameover, so reaching the goal (ReachedGoal -> WIN) wins first if you make
it. plan_speedrun_game: player at the near end -> goal at the far end, N killzone hazards that
RESPAWN you (bleeding the clock) between them. Distinct from time_survival (outlast a timer to
WIN) and collector_race (collect all before the clock): here you RACE A DEADLINE TO A PLACE.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script, normalize_behaviour, NEEDS_SCRIPT, _SCRIPT_TEMPLATES)
from unitytools.core.game_blueprint import (
    plan_speedrun_game, plan_game, compose_custom_game, BLUEPRINTS)
from unitytools.core.game_qa import (
    assess_game_readiness, studio_health, critique_design, game_howto_from_plan,
    build_game_howto, _BEHAVIOUR_CATEGORIES, _GAME_EXAMPLES)
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(prefix)}


# --- the deadline behaviour (mirror of timer) -------------------------------

def test_deadline_source_is_a_losing_countdown():
    s = generate_behaviour_script("deadline")
    assert s["ok"] is True and s["class_name"] == "AutopilotDeadline"
    src = s["source"]
    assert 'SendMessage("PlayerDied"' in src                    # the LOSE (mirror of timer's Survived)
    assert 'SendMessage("Survived"' not in src                  # NOT a win -- that is timer's job
    assert "remaining" in src and "Time.deltaTime" in src       # the countdown
    assert "Deadline" in src                                     # its own HUD label


def test_deadline_is_deterministic_ascii_balanced():
    src = generate_behaviour_script("deadline")["source"]
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


@pytest.mark.parametrize("alias", ["deadline", "zamanasimi", "sonsure", "songerisayim"])
def test_deadline_aliases(alias):
    assert normalize_behaviour(alias) == "deadline"


def test_deadline_does_not_collide_with_timer():
    # "sure"/"zaman" stay the WINNING timer; only the deadline-specific words map to deadline
    assert normalize_behaviour("sure") == "timer"
    assert normalize_behaviour("zaman") == "timer"


def test_deadline_registered_and_categorized():
    assert "deadline" in NEEDS_SCRIPT and "deadline" in _SCRIPT_TEMPLATES
    assert "deadline" in _BEHAVIOUR_CATEGORIES["game feel"]      # drift guard


# --- the blueprint ----------------------------------------------------------

def test_registered_as_nineteenth_game():
    assert "speedrun" in BLUEPRINTS
    assert plan_game("speedrun", 5)["game"] == "speedrun"
    assert len(BLUEPRINTS) >= 19


def test_layout_is_a_race_from_start_to_exit():
    plan = plan_speedrun_game(5)
    assert _beh_of(plan, "Player") == {"player"}
    assert _beh_of(plan, "Goal") == {"goal"}
    assert _beh_of(plan, "Hazard") == {"killzone"}
    assert _beh_of(plan, "GameManager") == {"deadline", "gameover", "title", "sound"}
    # five deadly hazards, each a killzone (respawn-on-touch)
    n_hazards = sum(1 for s in plan["steps"]
                    if s.get("script_behaviour", {}).get("behaviour") == "killzone")
    assert n_hazards == 5
    # the hazards are NOT tagged Enemy -- the only win is reaching the exit
    tags = {s["kwargs"].get("tag") for s in plan["steps"] if s.get("tool") == "unity_set_tag"}
    assert tags == {"Player"}


def test_critique_is_clean_a_goal_win_with_a_deadline_lose():
    # gameover + a goal to reach is a WIN trigger; the deadline is the LOSE. No notes.
    counts = {"player": 1, "goal": 1, "killzone": 5, "deadline": 1,
              "gameover": 1, "title": 1, "sound": 1}
    assert critique_design(counts) == []


def test_speedrun_is_clean_by_the_self_audit():
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    sr = next(g for g in h["games"] if g["game_type"] == "speedrun")
    assert sr["valid"] and sr["playable"] and sr["coherent"]


@pytest.mark.parametrize("seed", ["a", "b", "42", "dash"])
def test_valid_and_playable(seed):
    plan = plan_game("speedrun", 5, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True and r["has_goal"] is True
    assert r["design_notes"] == []


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("speedrun", 5, seed="x") == plan_game("speedrun", 5, seed="x")
    assert plan_game("speedrun", 5, seed="x") != plan_game("speedrun", 5, seed="y")
    assert plan_game("speedrun", 5, seed=None) == plan_game("speedrun", 5)


def test_hazard_count_clamped():
    assert plan_speedrun_game(0)["hazard_count"] == 1
    assert plan_speedrun_game(99)["hazard_count"] == 40


# --- how-to derivation (deadline-aware) -------------------------------------

def test_howto_is_about_racing_a_deadline_to_the_exit():
    h = game_howto_from_plan(plan_game("speedrun", 5))
    win = " ".join(h["win"]).lower()
    assert "reach the goal" in win and "before the deadline" in win
    assert any("deadline" in t.lower() for t in h["threats"])
    assert any("deadline runs out" in l.lower() for l in h["lose"])
    # the card renders, ascii + every section
    text = build_game_howto("speedrun")
    assert all(ord(c) < 128 for c in text)
    for section in ("## Controls", "## How to win", "## Watch out for", "## How you lose"):
        assert section in text


def test_deadline_lifts_a_composed_goal_game_into_a_speedrun_feel():
    # a freeform goal game gains the deadline pressure in its derived how-to
    base = game_howto_from_plan(compose_custom_game(player=True, goal=True, hazard=3))
    assert not any("deadline" in " ".join(v).lower() for v in base.values())
    # (the composer has no deadline element yet; this just proves the deriver is gated on it)


# --- showcase + intent ------------------------------------------------------

def test_showcase_example_present():
    assert "speedrun" in _GAME_EXAMPLES
    prompt, pitch = _GAME_EXAMPLES["speedrun"]
    assert pitch and all(ord(c) < 128 for c in prompt + pitch)


@pytest.mark.parametrize("prompt", [
    "speedrun oyunu kur", "speed run yap", "beat the clock game", "hizli bitir oyunu",
    "sure dolmadan cikis oyunu",
])
def test_speedrun_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "speedrun", prompt


def test_speedrun_does_not_steal_runner_dodge_or_the_clock_games():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("runner oyunu kur") == "runner"
    assert gt("endless runner yap") == "runner"
    assert gt("kacis oyunu yap") == "dodge"
    assert gt("sureli hayatta kalma oyunu") == "time_survival"
    assert gt("toplama yarisi yap") == "collector_race"
