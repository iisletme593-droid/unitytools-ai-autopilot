"""P12 (cycle 62): horde / survival-brawler blueprint — the 8th game type.

plan_horde_game arms the player fully (player/health/attack/ranged/score/xp/
inventory) and puts a central `horde` wave spawner in the arena. One initial enemy
(enemy + reward) ensures AutopilotEnemy.cs + AutopilotReward.cs get imported so the
horde spawner (which AddComponents them) compiles, and starts the arena populated.
"""
import pytest

from unitytools.core.game_blueprint import plan_horde_game, plan_game, BLUEPRINTS, group_execution_plan
from unitytools.core.game_qa import assess_game_readiness, INTERACTIVE_BEHAVIOURS
from unitytools.core.game_io import validate_plan


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


def test_registered_as_eighth_game():
    assert "horde" in BLUEPRINTS
    assert plan_game("horde", 4)["game"] == "horde"
    assert len(BLUEPRINTS) == 8


def test_player_is_fully_armed():
    plan = plan_horde_game(4)
    assert _beh_of(plan, "Player") == {"player", "health", "attack", "ranged", "score", "xp", "inventory"}


def test_central_horde_spawner():
    plan = plan_horde_game(4)
    assert _beh_of(plan, "Spawner") == {"horde"}


def test_initial_enemy_imports_enemy_and_reward_scripts():
    # one initial enemy ensures AutopilotEnemy + AutopilotReward are imported (the
    # horde spawner AddComponents them) and the arena starts populated
    plan = plan_horde_game(4)
    assert _beh_of(plan, "Enemy_0") == {"enemy", "reward"}
    grouped = group_execution_plan(plan["steps"])
    assert {"horde", "enemy", "reward"} <= set(grouped["script_behaviours"])


def test_horde_is_an_interactive_behaviour():
    assert "horde" in INTERACTIVE_BEHAVIOURS


def test_loot_scattered():
    plan = plan_horde_game(5)
    loot = [s["script_behaviour"]["object"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("behaviour") == "loot"]
    assert loot == [f"Loot_{i}" for i in range(5)]


@pytest.mark.parametrize("seed", ["a", "b", "wave", "9"])
def test_valid_and_playable(seed):
    plan = plan_game("horde", 4, seed=seed)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True


def test_deterministic_and_seed_none_is_plain():
    assert plan_game("horde", 4, seed="x") == plan_game("horde", 4, seed="x")
    assert plan_game("horde", 4, seed="x") != plan_game("horde", 4, seed="y")
    assert plan_game("horde", 4, seed=None) == plan_game("horde", 4)


def test_enemy_count_clamped():
    assert plan_horde_game(0)["enemy_count"] == 1
    assert plan_horde_game(99)["enemy_count"] == 30


def test_variations_work_for_horde():
    from unitytools.core.game_blueprint import plan_game_variations
    out = plan_game_variations("horde", counts=[2, 4, 6])
    assert [v["params"]["count"] for v in out["variations"]] == [2, 4, 6]
    assert all(v["playable"] for v in out["variations"])
