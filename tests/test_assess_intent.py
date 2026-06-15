"""P7 (cycle 34): bind game QA to natural language.

"oyunu degerlendir" / "assess the game" / "oynanabilir mi" route to
unity_assess_game (pure analysis), and must beat the build-game intent when a
prompt contains both a game type and an assess verb ("dodge oyununu degerlendir").
Scene-level "analiz"/"qa"/"performans" prompts (no game context) must NOT be
hijacked — they still reach the visual-QA / profiling branches.
"""
import pytest

from unitytools.core.game_studio_actions import plan_unity_fast_action


def _tool(prompt: str) -> str:
    steps = plan_unity_fast_action(prompt)["steps"]
    return steps[0]["tool"] if steps else ""


def _game_type(prompt: str):
    return plan_unity_fast_action(prompt)["steps"][0]["kwargs"].get("game_type")


@pytest.mark.parametrize("prompt,expected_type", [
    ("oyunu degerlendir", "collectathon"),
    ("dodge oyununu degerlendir", "dodge"),
    ("platformer oyununu analiz et", "platformer"),
    ("survival oyunu QA yap", "survival"),
    ("chase oyunu oynanabilir mi", "chase"),
    ("assess the dodge game", "dodge"),
    ("is the game playable", "collectathon"),
])
def test_assess_intents_route_to_assess(prompt, expected_type):
    assert _tool(prompt) == "unity_assess_game", prompt
    assert _game_type(prompt) == expected_type, prompt


def test_assess_beats_build_when_both_present():
    # "dodge oyununu degerlendir" has the game type 'dodge' AND the assess verb;
    # the assessment must win (it is checked before the build-game branch).
    assert _tool("dodge oyununu degerlendir") == "unity_assess_game"
    assert _tool("platformer oyununu degerlendir") == "unity_assess_game"


def test_build_intents_still_build():
    assert _tool("dodge oyunu yap") == "unity_build_simple_game"
    assert _tool("kovalamaca oyunu kur") == "unity_build_simple_game"
    assert _tool("toplama oyunu yap") == "unity_build_simple_game"
    assert _game_type("dodge oyunu yap") == "dodge"
    assert _game_type("kovalamaca oyunu kur") == "chase"


def test_scene_level_analysis_is_not_hijacked():
    # no game context -> these must reach their own (non-game) branches
    assert _tool("sahne performansini analiz et") == "unity_profile_scene_performance"
    assert _tool("kalite kontrol yap") == "unity_run_visual_qa"


def test_assess_step_is_read_only():
    step = plan_unity_fast_action("dodge oyununu degerlendir")["steps"][0]
    assert step["write"] is False
    assert step["kwargs"]["game_type"] == "dodge"
