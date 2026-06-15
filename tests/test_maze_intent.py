"""P10 (cycle 50): maze natural-language intent.

"labirent oyunu kur" / "maze game" route to a maze build; size and seed work
together ("labirent oyunu kur tohum 7" -> game_type=maze, seed=7); assess and
variations also recognise maze; the other game intents are unchanged.
"""
import pytest

from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.game_qa import build_game_capabilities_summary


def _kw(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["kwargs"]


def _tool(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["tool"]


@pytest.mark.parametrize("prompt", [
    "labirent oyunu kur",
    "labirent oyunu yap",
    "maze game build",
    "build me a maze game",
    "maze oyunu kur",
])
def test_maze_build_intent(prompt):
    kw = _kw(prompt)
    assert _tool(prompt) == "unity_build_simple_game"
    assert kw["game_type"] == "maze", prompt


def test_maze_size_and_seed_together():
    kw = _kw("labirent oyunu kur 6 tohum 7")
    assert kw["game_type"] == "maze"
    assert kw["collectible_count"] == 6        # size
    assert kw["seed"] == "7"                    # seed, kept separate from size


def test_maze_seed_only():
    kw = _kw("labirent oyunu kur tohum forest")
    assert kw["game_type"] == "maze" and kw["seed"] == "forest"


def test_maze_assess_and_variations():
    assert _tool("labirent oyununu degerlendir") == "unity_assess_game"
    assert _kw("labirent oyununu degerlendir")["game_type"] == "maze"
    assert _tool("labirent varyasyonlari goster") == "unity_game_variations"
    assert _kw("labirent varyasyonlari goster")["game_type"] == "maze"


def test_other_game_intents_unchanged():
    assert _kw("dodge oyunu yap")["game_type"] == "dodge"
    assert _kw("platform oyunu yap")["game_type"] == "platformer"
    assert _kw("chase oyunu kur")["game_type"] == "chase"
    assert _kw("toplama oyunu yap")["game_type"] == "collectathon"
    assert _kw("sag kalma oyunu yap")["game_type"] == "survival"


def test_capabilities_summary_lists_maze():
    # the summary is code-derived from the catalog, so maze appears automatically
    assert "maze" in build_game_capabilities_summary()
