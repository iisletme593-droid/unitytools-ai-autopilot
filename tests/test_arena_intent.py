"""P11 (cycle 55): arena natural-language intent.

"arena oyunu kur" / "dövüş / savaş oyunu" / "brawler" route to an arena build;
size and seed work together; assess/variations recognise arena; the other game
intents (especially survival, which is a different word) are unchanged.
"""
import pytest

from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.game_qa import build_game_capabilities_summary


def _kw(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["kwargs"]


def _tool(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["tool"]


@pytest.mark.parametrize("prompt", [
    "arena oyunu kur",
    "dovus oyunu yap",
    "savas oyunu kur",
    "build me a brawler",
    "combat game build",
])
def test_arena_build_intent(prompt):
    assert _tool(prompt) == "unity_build_simple_game"
    assert _kw(prompt)["game_type"] == "arena", prompt


def test_arena_size_and_seed():
    kw = _kw("arena oyunu kur 6 tohum 5")
    assert kw["game_type"] == "arena" and kw["collectible_count"] == 6 and kw["seed"] == "5"


def test_arena_assess_and_variations():
    assert _kw("arena oyununu degerlendir")["game_type"] == "arena"
    assert _tool("arena varyasyonlari goster") == "unity_game_variations"
    assert _kw("arena varyasyonlari goster")["game_type"] == "arena"


def test_savas_does_not_collide_with_survival():
    # "savaş" (war/combat) -> arena; "sağ kalma / hayatta kalma" -> survival
    assert _kw("savas oyunu kur")["game_type"] == "arena"
    assert _kw("sag kalma oyunu yap")["game_type"] == "survival"
    assert _kw("hayatta kalma oyunu kur")["game_type"] == "survival"


def test_other_game_intents_unchanged():
    assert _kw("dodge oyunu yap")["game_type"] == "dodge"
    assert _kw("labirent oyunu kur")["game_type"] == "maze"
    assert _kw("kovalamaca oyunu kur")["game_type"] == "chase"
    assert _kw("platform oyunu yap")["game_type"] == "platformer"
    assert _kw("toplama oyunu yap")["game_type"] == "collectathon"


def test_capabilities_summary_lists_arena():
    text = build_game_capabilities_summary()
    assert "arena" in text and "playable game types" in text
