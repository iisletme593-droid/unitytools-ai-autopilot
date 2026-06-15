"""P7 (cycle 36): difficulty + variations intents.

(a) A difficulty WORD in a build prompt sets the count (kolay->3, orta->5,
    zor->8), but an explicit number always wins.
(b) "varyasyon / seçenekler / farklı zorluklar" route to unity_game_variations
    (the easy/medium/hard options), beating the build intent when a game type is
    also present ("dodge varyasyonları göster").
"""
import pytest

from unitytools.core.game_studio_actions import plan_unity_fast_action


def _step(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]


def _count(prompt):
    return _step(prompt)["kwargs"]["collectible_count"]


@pytest.mark.parametrize("prompt,expected", [
    ("kolay dodge oyunu yap", 3),
    ("easy collectathon game build", 3),
    ("orta collectathon oyunu kur", 5),
    ("normal dodge oyunu yap", 5),
    ("zor dodge oyunu yap", 8),
    ("hard chase game build", 8),
    ("cok zor chase oyunu yap", 8),          # "zor" matches inside "cok zor"
    ("dodge oyunu yap", 5),                   # no difficulty word -> default
])
def test_difficulty_word_sets_count(prompt, expected):
    assert _step(prompt)["tool"] == "unity_build_simple_game"
    assert _count(prompt) == expected, prompt


@pytest.mark.parametrize("prompt,expected", [
    ("zor dodge oyunu yap 4 dusman", 4),      # explicit number beats "zor"
    ("kolay toplama oyunu yap 12", 12),       # explicit number beats "kolay"
    ("toplama oyunu yap 8", 8),
])
def test_explicit_number_beats_difficulty_word(prompt, expected):
    assert _count(prompt) == expected, prompt


@pytest.mark.parametrize("prompt,gtype", [
    ("dodge varyasyonlari goster", "dodge"),
    ("chase oyunu secenekleri", "chase"),
    ("platformer farkli zorluklar", "platformer"),
    ("survival oyunu variations", "survival"),
    ("collectathon zorluk secenekleri", "collectathon"),
])
def test_variations_intent_routes_to_variations(prompt, gtype):
    step = _step(prompt)
    assert step["tool"] == "unity_game_variations", prompt
    assert step["kwargs"]["game_type"] == gtype, prompt
    assert step["write"] is False


def test_variations_beats_build_when_game_type_present():
    # "dodge varyasyonlari goster" has the game type 'dodge' AND a variations verb;
    # the user wants the options, not one build.
    assert _step("dodge varyasyonlari goster")["tool"] == "unity_game_variations"


def test_build_without_difficulty_or_variations_is_unchanged():
    assert _step("dodge oyunu yap")["tool"] == "unity_build_simple_game"
    assert _step("kovalamaca oyunu kur")["tool"] == "unity_build_simple_game"


def test_cok_alone_is_not_a_difficulty_trigger():
    # "cok dusman" is a quantity, not a difficulty; with an explicit number it wins,
    # and "cok" by itself must not silently bump the count to hard.
    assert _count("cok dusman olan dodge oyunu yap 12") == 12
    assert _count("dodge oyunu yap") == 5      # plain default, "cok" absent
