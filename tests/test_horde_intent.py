"""P12 (cycle 63): horde natural-language intent + survival distinction.

"horde oyunu kur" / "dalga modu" / "akın oyunu" / "survival brawler" route to a
horde build; size+seed work together. Crucially "survival brawler" -> horde while
plain "sağ kalma / hayatta kalma / survival" -> survival (checked first). The other
game intents are unchanged.
"""
import pytest

from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.game_qa import build_game_capabilities_summary


def _kw(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["kwargs"]


def _tool(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["tool"]


@pytest.mark.parametrize("prompt", [
    "horde oyunu kur",
    "dalga modu oyunu yap",
    "akin oyunu kur",
    "survival brawler yap",
    "horde game build",
])
def test_horde_build_intent(prompt):
    assert _tool(prompt) == "unity_build_simple_game"
    assert _kw(prompt)["game_type"] == "horde", prompt


def test_horde_size_and_seed():
    kw = _kw("horde oyunu kur 6 tohum 5")
    assert kw["game_type"] == "horde" and kw["collectible_count"] == 6 and kw["seed"] == "5"


def test_survival_vs_horde_distinction():
    # the key disambiguation: "survival brawler" is a horde, plain survival is not
    assert _kw("survival brawler yap")["game_type"] == "horde"
    assert _kw("sag kalma oyunu yap")["game_type"] == "survival"
    assert _kw("hayatta kalma oyunu kur")["game_type"] == "survival"
    assert _kw("survival oyunu yap")["game_type"] == "survival"


def test_horde_assess_and_variations():
    assert _kw("horde oyununu degerlendir")["game_type"] == "horde"
    assert _tool("horde varyasyonlari goster") == "unity_game_variations"
    assert _kw("horde varyasyonlari goster")["game_type"] == "horde"


def test_other_game_intents_unchanged():
    assert _kw("arena oyunu kur")["game_type"] == "arena"
    assert _kw("dodge oyunu yap")["game_type"] == "dodge"
    assert _kw("labirent oyunu kur")["game_type"] == "maze"
    assert _kw("kovalamaca oyunu kur")["game_type"] == "chase"
    assert _kw("toplama oyunu yap")["game_type"] == "collectathon"


def test_capabilities_summary_lists_horde_and_eight_games():
    text = build_game_capabilities_summary()
    assert "horde" in text and "8 playable game types" in text
