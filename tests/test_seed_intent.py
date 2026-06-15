"""P9 (cycle 47): seed in natural language + seed survives save/load.

"tohum 42" / "seed 42" add a procedural seed to a build, WITHOUT the seed digit
being mistaken for the object count. A seeded plan's seed round-trips through
serialize/deserialize and disk save/load.
"""
import pytest

from unitytools.core.game_studio_actions import extract_seed, plan_unity_fast_action
from unitytools.core.game_blueprint import plan_game
from unitytools.core.game_io import serialize_plan, deserialize_plan, save_plan_to_file, load_plan_from_file


# --- pure seed extraction ---------------------------------------------------

@pytest.mark.parametrize("text,seed", [
    ("tohum 42", "42"),
    ("seed 7", "7"),
    ("seed:abc", "abc"),
    ("seed=99", "99"),
    ("tohum forest", "forest"),
    ("42 tohumu ile", "42"),
    ("forest tohumuyla", "forest"),
    ("dodge oyunu yap", None),
    ("tohumu olmayan oyun", None),   # "tohumu" with no value before/after the keyword form
])
def test_extract_seed(text, seed):
    assert extract_seed(text)[0] == seed


def test_extract_seed_strips_the_span():
    seed, rest = extract_seed("dodge oyunu yap tohum 7")
    assert seed == "7"
    assert "7" not in rest                 # the seed digit is removed from the rest


# --- seed in the build intent (separate from count) -------------------------

def _kw(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["kwargs"]


def test_seed_added_to_build_kwargs():
    kw = _kw("dodge oyunu kur tohum 7")
    assert kw["game_type"] == "dodge" and kw["seed"] == "7"


def test_seed_digit_not_read_as_count():
    # "zor" -> 8, seed 7 must not become the count
    kw = _kw("zor dodge oyunu kur tohum 7")
    assert kw["collectible_count"] == 8 and kw["seed"] == "7"


def test_explicit_count_and_seed_coexist():
    kw = _kw("dodge oyunu yap 5 tohum 12")
    assert kw["collectible_count"] == 5 and kw["seed"] == "12"


def test_no_seed_means_no_seed_kwarg():
    assert "seed" not in _kw("dodge oyunu yap")
    assert "seed" not in _kw("dodge oyunu yap 8")


def test_word_seed_works():
    assert _kw("kolay chase oyunu yap tohum forest") == {
        "game_type": "chase", "collectible_count": 3, "execute": False, "seed": "forest"
    }


# --- seed survives persistence ----------------------------------------------

def test_seed_survives_serialize_round_trip():
    plan = plan_game("dodge", 5, seed="42")
    restored = deserialize_plan(serialize_plan(plan))
    assert restored.get("seed") == "42" and restored == plan


def test_seed_survives_disk_save_load(tmp_path):
    plan = plan_game("chase", 4, seed="boss-seed")
    save_plan_to_file(plan, "seeded", root=tmp_path)
    loaded = load_plan_from_file("seeded", root=tmp_path)
    assert loaded.get("seed") == "boss-seed" and loaded == plan


def test_unseeded_save_has_no_seed(tmp_path):
    save_plan_to_file(plan_game("dodge", 3), "plain", root=tmp_path)
    assert "seed" not in load_plan_from_file("plain", root=tmp_path)
