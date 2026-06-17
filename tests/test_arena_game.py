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


def test_registered_in_catalog():
    assert "arena" in BLUEPRINTS
    assert plan_game("arena", 4)["game"] == "arena"


def test_player_is_armed_with_health_score_xp_and_inventory():
    plan = plan_arena_game(4)
    assert _beh_of(plan, "Player") == {"player", "health", "attack", "score", "xp", "inventory"}
    tags = {s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
            and s["kwargs"]["name"] == "Player"}
    assert tags == {"Player"}


def test_arena_scatters_loot_to_collect():
    plan = plan_arena_game(5)
    loot = [s["script_behaviour"]["object"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("behaviour") == "loot"]
    assert loot == [f"Loot_{i}" for i in range(5)]


def test_enemies_are_tagged_enemy_with_ai_and_reward():
    plan = plan_arena_game(5)
    enemy_tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                  and s["kwargs"]["name"].startswith("Enemy")]
    assert enemy_tags == ["Enemy"] * 5            # every enemy tagged Enemy
    # enemy AI + reward (its HP + XP loot); NOT health, so the player's attack does
    # single damage to one TakeDamage receiver
    assert _beh_of(plan, "Enemy") == {"enemy", "reward"}


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


def test_manager_bookends_with_title_gameover_and_sound():
    plan = plan_arena_game(4)
    # the hidden GameManager runs the bookends (title start screen + gameover win/lose)
    # plus a sound cue gameover SendMessages "PlayCue" to on the win/lose transition
    assert _beh_of(plan, "GameManager") == {"title", "gameover", "sound"}


def test_groups_to_fourteen_unique_scripts():
    grouped = group_execution_plan(plan_arena_game(4)["steps"])
    assert set(grouped["script_behaviours"]) == {
        "player", "health", "attack", "score", "xp", "inventory",
        "enemy", "reward", "loot", "title", "gameover", "sound", "boss", "hitflash"}


def test_arena_has_a_single_mini_boss():
    plan = plan_arena_game(4)
    # one elite Boss, tagged Enemy (so the clear-all-enemies WIN includes it), running the
    # high-HP boss behaviour -- and it is NOT one of the Enemy_* swarm
    assert _beh_of(plan, "Boss") == {"boss", "hitflash"}      # boss + juice (flash on hit)
    boss_tags = [s["kwargs"]["tag"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                 and s["kwargs"]["name"] == "Boss"]
    assert boss_tags == ["Enemy"]
    # the swarm assertions are unaffected: the Enemy_* count still matches enemy_count
    enemy_swarm = [s["kwargs"]["name"] for s in plan["steps"] if s.get("tool") == "unity_set_tag"
                   and s["kwargs"]["name"].startswith("Enemy")]
    assert enemy_swarm == [f"Enemy_{i}" for i in range(4)]


def test_arena_with_boss_is_coherent_by_the_self_audit():
    from unitytools.core.game_qa import studio_health
    h = studio_health()
    arena = next(g for g in h["games"] if g["game_type"] == "arena")
    assert arena["valid"] and arena["playable"] and arena["coherent"]


def test_variations_work_for_arena():
    from unitytools.core.game_blueprint import plan_game_variations
    out = plan_game_variations("arena", counts=[2, 4, 6])
    assert [v["params"]["count"] for v in out["variations"]] == [2, 4, 6]
    assert all(v["playable"] for v in out["variations"])
