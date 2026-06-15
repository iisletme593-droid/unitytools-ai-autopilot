"""P11 (cycle 56): arena end-to-end — intent x persistence x variations x assess.

Proves the arena combat game works through the whole studio: a natural-language
intent builds it, it serializes + saves + loads IDENTICALLY, it varies across
sizes (all playable), assesses as playable, and a re-imported plan validates.
Pure, tmp_path.
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


def test_intent_to_save_to_load_is_identical(tmp_path):
    plan = _plan_from_intent("arena oyunu kur 4 tohum 9")
    assert plan["game"] == "arena" and plan["seed"] == "9"
    assert deserialize_plan(serialize_plan(plan)) == plan
    save_plan_to_file(plan, "my-arena", root=tmp_path)
    assert load_plan_from_file("my-arena", root=tmp_path) == plan
    assert _plan_from_intent("arena oyunu kur 4 tohum 9") == plan


def test_same_seed_other_session_same_arena(tmp_path):
    a = plan_game("arena", 5, seed="boss-wave")
    save_plan_to_file(a, "saved", root=tmp_path)
    assert load_plan_from_file("saved", root=tmp_path) == plan_game("arena", 5, seed="boss-wave") == a


def test_arena_variations_all_playable():
    out = plan_game_variations("arena", counts=[2, 4, 6])
    assert [v["params"]["count"] for v in out["variations"]] == [2, 4, 6]
    assert all(v["playable"] for v in out["variations"])
    objs = [v["object_count"] for v in out["variations"]]
    assert objs == sorted(objs) and len(set(objs)) == 3


def test_arena_assess_playable_with_player():
    r = assess_game_readiness(plan_game("arena", 4, seed="x"))
    assert r["playable"] is True and r["has_player"] is True


def test_imported_arena_plan_validates():
    plan = deserialize_plan(serialize_plan(plan_game("arena", 4, seed="imp")))
    assert validate_plan(plan)["ok"] is True
