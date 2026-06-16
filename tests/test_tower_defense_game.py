"""P14 (cycle 73): tower-defense -- the 10th game type, built entirely from existing
blocks (no new behaviour).

The trick: enemies' target is a stationary BASE tagged Player + `health` (the existing
enemy AI FindWithTag("Player") marches to it; when it falls -> SendMessage PlayerDied
-> gameover LOSE). It's defended by a line of `ranged` towers (auto-target the nearest
Enemy) and a mobile hero (`player` controller -> the scene assesses playable) who is
NOT tagged Player, so enemies ignore the hero and head for the base. WIN clears enemies.
"""
import pytest

from unitytools.core.game_blueprint import (
    plan_tower_defense_game, plan_game, BLUEPRINTS, group_execution_plan)
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import plan_unity_fast_action


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


def _tag_of(plan, obj):
    return {s["kwargs"]["tag"] for s in plan["steps"]
            if s.get("tool") == "unity_set_tag" and s["kwargs"]["name"] == obj}


def test_registered_as_tenth_game():
    assert "tower_defense" in BLUEPRINTS
    assert plan_game("tower_defense", 6)["game"] == "tower_defense"
    assert len(BLUEPRINTS) >= 10


def test_base_is_the_enemy_target_and_the_lose_condition():
    plan = plan_tower_defense_game(6)
    # the base is tagged Player (so the enemy AI targets it) and has health (falls -> lose)
    assert _beh_of(plan, "Base") == {"health"}
    assert _tag_of(plan, "Base") == {"Player"}


def test_hero_is_the_controllable_avatar_not_tagged_player():
    plan = plan_tower_defense_game(6)
    # the hero carries the player controller (keeps the game playable) + a melee attack,
    # but is NOT tagged Player, so enemies head for the base instead of the hero
    assert _beh_of(plan, "Hero") == {"player", "attack", "score"}
    assert _tag_of(plan, "Hero") == set()


def test_towers_are_ranged_auto_attackers():
    plan = plan_tower_defense_game(6)
    towers = sorted(s["script_behaviour"]["object"] for s in plan["steps"]
                    if s.get("script_behaviour", {}).get("behaviour") == "ranged")
    assert towers and all(t.startswith("Tower_") for t in towers)


def test_enemies_are_tagged_and_marching_and_killable():
    plan = plan_tower_defense_game(5)
    enemy_tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                  and s["kwargs"]["name"].startswith("Enemy")]
    assert enemy_tags == ["Enemy"] * 5
    assert _beh_of(plan, "Enemy_0") == {"enemy", "reward"}


def test_has_the_feel_loop_manager():
    plan = plan_tower_defense_game(6)
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}


def test_reuses_only_existing_behaviours_no_new_template():
    # tower-defense must not introduce a new scripted behaviour; it is pure recomposition
    from unitytools.core.gameplay import _SCRIPT_TEMPLATES
    used = {s["script_behaviour"]["behaviour"] for s in plan_tower_defense_game(6)["steps"]
            if "script_behaviour" in s}
    assert used <= set(_SCRIPT_TEMPLATES), f"unknown behaviours: {used - set(_SCRIPT_TEMPLATES)}"


@pytest.mark.parametrize("seed", ["a", "b", "42", "td"])
def test_valid_and_playable(seed):
    plan = plan_game("tower_defense", 6, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("tower_defense", 6, seed="x") == plan_game("tower_defense", 6, seed="x")
    assert plan_game("tower_defense", 6, seed="x") != plan_game("tower_defense", 6, seed="y")
    assert plan_game("tower_defense", 6, seed=None) == plan_game("tower_defense", 6)


def test_enemy_count_clamped_and_towers_scale():
    assert plan_tower_defense_game(0)["enemy_count"] == 1
    assert plan_tower_defense_game(99)["enemy_count"] == 30
    assert plan_tower_defense_game(6)["tower_count"] == 3       # max(2, (n+1)//2)
    assert plan_tower_defense_game(1)["tower_count"] == 2       # floor at 2


# --- intent ----------------------------------------------------------------

@pytest.mark.parametrize("prompt", [
    "tower defense oyunu kur",
    "tower-defense yap",
    "kule savunma oyunu kur",
    "kule savunmasi yap",
    "td oyunu kur",
])
def test_tower_defense_build_intent(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game"
    assert step["kwargs"]["game_type"] == "tower_defense", prompt


def test_tower_defense_does_not_steal_other_intents():
    def gt(p):
        return plan_unity_fast_action(p)["steps"][0]["kwargs"].get("game_type")
    assert gt("arena oyunu kur") == "arena"
    assert gt("dodge oyunu yap") == "dodge"
    assert gt("runner oyunu kur") == "runner"
    assert gt("toplama oyunu yap") == "collectathon"


def test_variations_work_for_tower_defense():
    from unitytools.core.game_blueprint import plan_game_variations
    out = plan_game_variations("tower_defense", counts=[3, 6, 9])
    assert [v["params"]["count"] for v in out["variations"]] == [3, 6, 9]
    assert all(v["playable"] for v in out["variations"])
