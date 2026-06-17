"""Cycle 104: game anatomy -- a single-game DEEP-DIVE report (the 6th self-awareness surface).

build_game_anatomy(game_type) is the 'zoom in on one game' counterpart to the catalog-wide
reports: for ONE type it shows the size (object + unique-script counts), behaviours grouped
by category, the build phases (geometry -> import unique scripts -> attach), the playability
verdict, and the example prompt. All code-derived from plan_game + assess + group_execution_plan,
so it never drifts. Exposed as unity_game_anatomy + the "X oyununun yapisi / anatomi" intent.
"""
import pytest

import unitytools.tools  # noqa: F401 - register @tools
from unitytools.core.game_qa import build_game_anatomy, _GAME_EXAMPLES, _BEHAVIOUR_CATEGORIES
from unitytools.core.game_blueprint import BLUEPRINTS, plan_game, group_execution_plan
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools


# --- the report -------------------------------------------------------------

@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_anatomy_is_pure_ascii_and_nonempty_for_every_type(game_type):
    text = build_game_anatomy(game_type)
    assert text and all(ord(c) < 128 for c in text)
    assert f"`{game_type}`" in text
    # the curated example prompt is shown
    assert _GAME_EXAMPLES[game_type][0] in text


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_anatomy_numbers_match_the_plan(game_type):
    plan = plan_game(game_type, 4)
    report = assess_game_readiness(plan)
    grouped = group_execution_plan(plan["steps"])
    text = build_game_anatomy(game_type, 4)
    # the headline make-up line is code-derived from the same plan
    assert f"{report['object_count']} objects" in text
    assert f"{report['unique_scripts']} unique" in text
    # the build-phase script list is the real grouped unique-script list
    for script in grouped["script_behaviours"]:
        assert script in text


def test_anatomy_groups_behaviours_by_category():
    text = build_game_anatomy("arena")
    # arena spans several categories -- they appear as headed bullets
    assert "## Behaviours by category" in text
    assert "**control**" in text and "**combat**" in text and "**game feel**" in text
    # the boss + hitflash (arena's mini-boss juice) show up under combat / game feel
    assert "boss" in text and "hitflash" in text


def test_anatomy_shows_build_phases_and_physics():
    maze = build_game_anatomy("maze")
    assert "## Build phases" in maze
    # the maze's solid walls are a physics behaviour (static_obstacle), surfaced separately
    assert "**physics**" in maze and "static_obstacle" in maze


def test_unknown_type_falls_back_to_collectathon():
    assert "`collectathon`" in build_game_anatomy("nonsense-type")


# --- tool + intent ----------------------------------------------------------

def test_tool_is_registered_and_pure():
    tool = {t.name: t for t in get_all_tools()}.get("unity_game_anatomy")
    assert tool is not None
    out = tool.fn(game_type="twin_stick")
    assert out["ok"] is True and out["game_type"] == "twin_stick"
    assert "Game anatomy" in out["anatomy"]
    # an unknown type is coerced to a real one (no crash)
    assert tool.fn(game_type="zzz")["game_type"] == "collectathon"


@pytest.mark.parametrize("prompt,gt", [
    ("arena oyununun yapisi", "arena"),
    ("maze oyunu anatomisi", "maze"),
    ("twin stick oyunu breakdown", "twin_stick"),
    ("boss oyunu neyden olusuyor", "boss"),
    ("dodge oyununun yapisi nedir", "dodge"),
])
def test_anatomy_intent_routes(prompt, gt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_game_anatomy", prompt
    assert step["kwargs"]["game_type"] == gt, prompt


def test_anatomy_intent_does_not_steal_build_assess_or_showcase():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    # a plain build / "yap" must NOT be read as "yapisi"
    assert tool("arena oyunu kur") == "unity_build_simple_game"
    assert tool("dodge oyunu yapsana") == "unity_build_simple_game"
    # assess + showcase keep their own intents
    assert tool("arena oyununu degerlendir") == "unity_assess_game"
    assert tool("ornek oyunlar goster") == "unity_game_showcase"
    assert tool("hangi oyunlar yapabilirsin") == "unity_game_catalog"
