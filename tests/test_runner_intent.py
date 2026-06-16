"""P14 (cycle 70): endless-runner natural-language intent.

"runner oyunu kur" / "endless runner yap" / "koşu oyunu" route to a runner build.
Its trigger terms (runner/endless/koşu/koşma/sonsuz koşu) are distinct from every
other game type, so detection is unambiguous and the other intents are unchanged --
in particular "koşma" must NOT be read as dodge ("kaçma").
"""
import pytest

from unitytools.core.game_studio_actions import plan_unity_fast_action


def _kw(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["kwargs"]


def _tool(prompt):
    return plan_unity_fast_action(prompt)["steps"][0]["tool"]


@pytest.mark.parametrize("prompt", [
    "runner oyunu kur",
    "endless runner yap",
    "kosu oyunu yap",
    "kosma oyunu kur",
    "sonsuz kosu oyunu olustur",
    "build me a runner game",
])
def test_runner_build_intent(prompt):
    assert _tool(prompt) == "unity_build_simple_game"
    assert _kw(prompt)["game_type"] == "runner", prompt


def test_runner_size_and_seed():
    kw = _kw("runner oyunu kur 10 tohum 7")
    assert kw["game_type"] == "runner" and kw["collectible_count"] == 10 and kw["seed"] == "7"


def test_runner_does_not_steal_other_intents():
    # the other game types still detect correctly; runner must not shadow them
    assert _kw("dodge oyunu yap")["game_type"] == "dodge"
    assert _kw("kacma oyunu kur")["game_type"] == "dodge"        # NOT runner
    assert _kw("horde oyunu kur")["game_type"] == "horde"
    assert _kw("arena oyunu kur")["game_type"] == "arena"
    assert _kw("toplama oyunu yap")["game_type"] == "collectathon"


def test_runner_is_generate_only():
    # like every build intent, planning a runner never triggers a live recompile
    assert _kw("runner oyunu kur")["execute"] is False
