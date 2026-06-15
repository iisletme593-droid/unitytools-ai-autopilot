"""P10 (cycle 51): maze end-to-end — intent x persistence x variations x assess.

Proves the maze game type works through the WHOLE studio pipeline: a natural-
language intent builds it, it serializes + saves + loads back IDENTICALLY
(deterministic), it varies across sizes (all playable), it assesses as playable,
and a re-imported maze plan validates. Pure, tmp_path.
"""
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.game_blueprint import plan_game, plan_game_variations
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_io import (
    serialize_plan, deserialize_plan, save_plan_to_file, load_plan_from_file, validate_plan,
)


def _plan_from_intent(prompt):
    kw = plan_unity_fast_action(prompt)["steps"][0]["kwargs"]
    return plan_game(kw["game_type"], kw["collectible_count"], seed=kw.get("seed"))


def test_intent_to_plan_to_save_to_load_is_identical(tmp_path):
    # NL intent -> plan -> serialize round-trip -> disk round-trip, all identical
    plan = _plan_from_intent("labirent oyunu kur 5 tohum 7")
    assert plan["game"] == "maze" and plan["seed"] == "7"

    assert deserialize_plan(serialize_plan(plan)) == plan       # serialize round-trip
    save_plan_to_file(plan, "my-maze", root=tmp_path)
    assert load_plan_from_file("my-maze", root=tmp_path) == plan  # disk round-trip

    # and rebuilding from the same intent yields the same maze (deterministic)
    assert _plan_from_intent("labirent oyunu kur 5 tohum 7") == plan


def test_same_seed_different_session_same_maze(tmp_path):
    a = plan_game("maze", 6, seed="shared-seed")
    save_plan_to_file(a, "shared", root=tmp_path)
    loaded = load_plan_from_file("shared", root=tmp_path)
    fresh = plan_game("maze", 6, seed="shared-seed")            # "another session"
    assert loaded == fresh == a                                 # byte-identical maze


def test_maze_variations_all_playable():
    out = plan_game_variations("maze", counts=[3, 5, 7])
    assert [v["params"]["count"] for v in out["variations"]] == [3, 5, 7]
    assert all(v["playable"] for v in out["variations"])
    # bigger maze -> more objects (monotonic)
    objs = [v["object_count"] for v in out["variations"]]
    assert objs == sorted(objs) and len(set(objs)) == 3


def test_maze_assess_playable_with_player_and_goal():
    r = assess_game_readiness(plan_game("maze", 5, seed="x"))
    assert r["playable"] is True and r["has_player"] is True and r["has_goal"] is True


def test_imported_maze_plan_validates():
    text = serialize_plan(plan_game("maze", 5, seed="imp"))
    plan = deserialize_plan(text)
    assert validate_plan(plan)["ok"] is True                    # walls/player/goal all whitelisted
