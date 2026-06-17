"""Cycle 109: game how-to -- a PLAYER-FACING 'how to play' card (the 7th self-awareness surface).

build_game_howto(game_type) derives the controls, how to win, the threats, and how to lose
straight from a game's behaviours (game_howto_from_plan), so it is honest + drift-free and
works on ANY plan -- a preset OR a freeform composed game (where there is no hand-written
description). The player-facing counterpart to the (technical) anatomy report.
"""
import pytest

import unitytools.tools  # noqa: F401 - register @tools
from unitytools.core.game_qa import build_game_howto, game_howto_from_plan
from unitytools.core.game_blueprint import BLUEPRINTS, plan_game, compose_custom_game
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools


# --- the card has every section and is honest about the win -----------------

@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_howto_has_all_sections_and_is_ascii(game_type):
    text = build_game_howto(game_type)
    assert text and all(ord(c) < 128 for c in text)
    for section in ("## Controls", "## How to win", "## Watch out for", "## How you lose"):
        assert section in text, (game_type, section)
    assert f"`{game_type}`" in text


@pytest.mark.parametrize("game_type,needle", [
    ("collectathon", "Reach the goal"),
    ("stealth", "Reach the goal"),
    ("puzzle", "Push every crate"),
    ("hold", "hold it until the meter"),
    ("collector_race", "before the countdown"),
    ("escort", "Guide the VIP"),
    ("arena", "Defeat every enemy"),
    ("twin_stick", "Defeat every enemy"),
    ("time_survival", "Outlast the countdown"),
    ("runner", "endless"),
])
def test_win_condition_matches_the_game(game_type, needle):
    win = " ".join(game_howto_from_plan(plan_game(game_type, 4))["win"])
    assert needle.lower() in win.lower(), (game_type, win)


def test_threats_and_lose_are_derived():
    # stealth: guards catch you on sight -> that is also how you lose
    h = game_howto_from_plan(plan_game("stealth", 4))
    assert any("guards" in t for t in h["threats"])
    assert any("guard spots you" in l.lower() for l in h["lose"])
    # boss: a high-HP boss is a threat and health is the lose path
    hb = game_howto_from_plan(plan_game("boss", 1))
    assert any("boss" in t for t in hb["threats"])
    assert any("health runs out" in l.lower() for l in hb["lose"])


def test_controls_reflect_the_kit():
    # twin-stick: auto-aim gun, no melee
    c = " ".join(game_howto_from_plan(plan_game("twin_stick", 4))["controls"])
    assert "auto-aim" in c.lower()
    # runner: auto-run
    cr = " ".join(game_howto_from_plan(plan_game("runner", 6))["controls"])
    assert "auto-run" in cr.lower()


def test_works_on_a_composed_game_too():
    # the whole point: a how-to can be derived for a freeform custom game with no preset summary
    plan = compose_custom_game(player=True, enemy=4, ranged=True)
    h = game_howto_from_plan(plan)
    assert any("Defeat every enemy" in w for w in h["win"])
    assert any("auto-aim" in c.lower() for c in h["controls"])
    assert any("health runs out" in l.lower() for l in h["lose"])


# --- tool + intent ----------------------------------------------------------

def test_tool_is_registered_and_pure():
    tool = {t.name: t for t in get_all_tools()}.get("unity_game_howto")
    assert tool is not None
    out = tool.fn(game_type="maze")
    assert out["ok"] is True and out["game_type"] == "maze"
    assert "How to play" in out["howto"]
    assert tool.fn(game_type="zzz")["game_type"] == "collectathon"


@pytest.mark.parametrize("prompt,gt", [
    ("arena oyunu nasil oynanir", "arena"),
    ("maze nasil oynaniyor", "maze"),
    ("twin stick oyunu kontrolleri", "twin_stick"),
    ("boss oyunu nasil oynanir", "boss"),
    ("how to play the runner game", "runner"),
])
def test_howto_intent_routes(prompt, gt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_game_howto", prompt
    assert step["kwargs"]["game_type"] == gt, prompt


def test_howto_intent_does_not_steal_build_anatomy_assess_or_showcase():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    assert tool("arena oyunu kur") == "unity_build_simple_game"
    assert tool("arena oyununun yapisi") == "unity_game_anatomy"
    assert tool("arena oyununu degerlendir") == "unity_assess_game"
    assert tool("ornek oyunlar goster") == "unity_game_showcase"
    assert tool("arena kampanyasi kur") == "unity_plan_campaign"
