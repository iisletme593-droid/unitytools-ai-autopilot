"""P9 (cycle 45): deterministic seeded RNG + seeded game plans.

seeded_rng(seed) is a pure splitmix64 generator: same seed -> same sequence,
forever, with no system time. plan_game(game_type, count, seed=...) uses it to
give a plan reproducible jitter — the same seed yields an identical plan, a
different seed a different (but deterministic) one, and seed=None is unchanged.
"""
import pytest

from unitytools.core.procedural import seeded_rng, SeededRng
from unitytools.core.game_blueprint import plan_game


# --- the RNG ---------------------------------------------------------------

def test_same_seed_same_sequence():
    a = [seeded_rng("level-1")._next() for _ in range(20)]  # noqa: SLF001
    b = [seeded_rng("level-1")._next() for _ in range(20)]  # noqa: SLF001
    assert a == b


def test_different_seeds_differ():
    a = [seeded_rng("alpha").random() for _ in range(10)]
    b = [seeded_rng("beta").random() for _ in range(10)]
    assert a != b


def test_random_in_unit_interval():
    rng = seeded_rng(42)
    for _ in range(1000):
        v = rng.random()
        assert 0.0 <= v < 1.0


def test_uniform_bounds():
    rng = seeded_rng("u")
    for _ in range(1000):
        v = rng.uniform(3.0, 9.0)
        assert 3.0 <= v < 9.0


def test_randint_inclusive_bounds():
    rng = seeded_rng("r")
    seen = set()
    for _ in range(2000):
        v = rng.randint(1, 6)
        assert 1 <= v <= 6
        seen.add(v)
    assert seen == {1, 2, 3, 4, 5, 6}          # covers the whole inclusive range


def test_randint_degenerate():
    assert seeded_rng("x").randint(5, 5) == 5
    assert seeded_rng("x").randint(7, 3) == 7   # high <= low -> low


def test_choice_and_shuffle_are_deterministic():
    items = list(range(10))
    assert seeded_rng("s").choice(items) == seeded_rng("s").choice(items)
    assert seeded_rng("s").shuffle(items) == seeded_rng("s").shuffle(items)
    # shuffle is a permutation, not the identity for this seed
    sh = seeded_rng("s").shuffle(items)
    assert sorted(sh) == items and sh != items


def test_int_and_str_seeds_both_work():
    assert isinstance(seeded_rng(123), SeededRng)
    assert seeded_rng(123).random() == seeded_rng(123).random()


# --- seeded plans ----------------------------------------------------------

def test_seed_none_is_plain_blueprint():
    assert plan_game("dodge", 5, seed=None) == plan_game("dodge", 5)
    assert "seed" not in plan_game("dodge", 5)


def test_same_seed_same_plan():
    assert plan_game("chase", 4, seed="abc") == plan_game("chase", 4, seed="abc")


def test_different_seed_different_jitter():
    a = plan_game("dodge", 5, seed="one")
    b = plan_game("dodge", 5, seed="two")
    assert a != b
    ja = [s["kwargs"]["jitter"] for s in a["steps"] if s.get("tool") == "unity_place_primitives"]
    jb = [s["kwargs"]["jitter"] for s in b["steps"] if s.get("tool") == "unity_place_primitives"]
    assert ja and jb and ja != jb


def test_seed_recorded_and_jitter_bounded():
    plan = plan_game("collectathon", 5, seed="lvl7")
    assert plan["seed"] == "lvl7"
    assert "[seed lvl7]" in plan["summary"]
    for s in plan["steps"]:
        if s.get("tool") == "unity_place_primitives":
            assert 0.5 <= s["kwargs"]["jitter"] < 2.0


def test_seeded_plan_still_validates_and_is_playable():
    from unitytools.core.game_qa import assess_game_readiness
    from unitytools.core.game_io import validate_plan
    plan = plan_game("chase", 5, seed="seedy")
    assert validate_plan(plan)["ok"] is True       # jitter is a primitive kwarg
    assert assess_game_readiness(plan)["playable"] is True


def test_build_tool_accepts_seed(monkeypatch):
    import unitytools.tools.unity_tools as ut
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_build_simple_game(collectible_count=4, game_type="dodge", seed="s1")
    assert r["dry_run"] is True and r["seed"] == "s1"
    assert ut.unity_build_simple_game(4, game_type="dodge", seed="s1") == \
           ut.unity_build_simple_game(4, game_type="dodge", seed="s1")
