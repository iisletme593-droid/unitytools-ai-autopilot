"""P11 (cycle 54): arena/brawler blueprint — the 7th game type.

plan_arena_game wires the combat trio into a playable game: an armed player
(player + health + attack + score, tag Player) versus N enemies (tag Enemy, with
the enemy AI + their own health) — mutual combat. Player attack defaults to
targetTag "Enemy"; enemies target the Player. Deterministic, valid, playable.
"""
import pytest

from unitytools.core.game_blueprint import plan_arena_game, plan_game, BLUEPRINTS, group_execution_plan
from unitytools.core.game_qa import assess_game_readiness, INTERACTIVE_BEHAVIOURS
from unitytools.core.game_io import validate_plan
from unitytools.core.gameplay import generate_behaviour_script

SEEDS = ["a", "b", "42", "fight"]


def _beh_of(plan, obj_prefix):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if str(s.get("script_behaviour", {}).get("object", "")).startswith(obj_prefix)}


def test_registered_as_seventh_game():
    assert "arena" in BLUEPRINTS
    assert plan_game("arena", 4)["game"] == "arena"
    assert len(BLUEPRINTS) == 7


def test_player_is_armed_with_health_and_score():
    plan = plan_arena_game(4)
    assert _beh_of(plan, "Player") == {"player", "health", "attack", "score"}
    tags = {s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"] == "Player"}
    assert tags == {"Player"}


def test_enemies_are_tagged_enemy_with_ai_and_health():
    plan = plan_arena_game(5)
    enemy_tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                  and s["kwargs"]["name"].startswith("Enemy")]
    assert enemy_tags == ["Enemy"] * 5            # every enemy tagged Enemy
    assert _beh_of(plan, "Enemy") == {"enemy", "health"}


def test_mutual_combat_targets():
    # player's attack hits "Enemy" by default; the enemy AI hits the Player
    attack = generate_behaviour_script("attack")["source"]
    enemy = generate_behaviour_script("enemy")["source"]
    assert 'targetTag = "Enemy"' in attack
    assert 'FindWithTag("Player")' in enemy


def test_enemy_is_an_interactive_behaviour():
    assert "enemy" in INTERACTIVE_BEHAVIOURS


@pytest.mark.parametrize("seed", SEEDS)
def test_valid_and_playable(seed):
    plan = plan_game("arena", 4, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("arena", 4, seed="x") == plan_game("arena", 4, seed="x")
    assert plan_game("arena", 4, seed="x") != plan_game("arena", 4, seed="y")
    assert plan_game("arena", 4, seed=None) == plan_game("arena", 4)


def test_enemy_count_clamped():
    assert plan_arena_game(0)["enemy_count"] == 1
    assert plan_arena_game(99)["enemy_count"] == 30


def test_groups_to_five_unique_scripts():
    grouped = group_execution_plan(plan_arena_game(4)["steps"])
    assert set(grouped["script_behaviours"]) == {"player", "health", "attack", "score", "enemy"}


def test_variations_work_for_arena():
    from unitytools.core.game_blueprint import plan_game_variations
    out = plan_game_variations("arena", counts=[2, 4, 6])
    assert [v["params"]["count"] for v in out["variations"]] == [2, 4, 6]
    assert all(v["playable"] for v in out["variations"])
