"""P14 (cycle 80): multi-level campaigns -- an ordered, increasing-difficulty sequence
of full playable levels of one game type. A new structural axis on top of the blueprints.
"""
import pytest

from unitytools.core.game_blueprint import plan_campaign, BLUEPRINTS
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.game_io import validate_plan
from unitytools.core.game_qa import assess_game_readiness
from unitytools.core.tool_registry import get_all_tools
import unitytools.tools  # noqa: F401 - register tools


# --- the campaign planner ---------------------------------------------------

def test_campaign_is_ordered_and_climbs_in_difficulty():
    camp = plan_campaign("arena", 3)
    assert camp["kind"] == "campaign" and camp["game_type"] == "arena"
    assert camp["level_count"] == 3
    levels = camp["levels"]
    assert [lv["level"] for lv in levels] == [1, 2, 3]
    counts = [lv["count"] for lv in levels]
    assert counts == sorted(counts) and len(set(counts)) == 3        # strictly climbing
    assert [lv["label"] for lv in levels] == ["easy", "medium", "hard"]


def test_every_level_is_a_full_playable_plan():
    camp = plan_campaign("arena", 4)
    assert camp["all_playable"] is True
    for lv in camp["levels"]:
        assert "steps" in lv["plan"]                                # the full buildable plan
        assert validate_plan(lv["plan"])["ok"] is True
        assert assess_game_readiness(lv["plan"])["playable"] is True


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_campaign_works_for_every_blueprint(game_type):
    camp = plan_campaign(game_type, 3)
    assert camp["all_playable"] is True and len(camp["levels"]) == 3


def test_campaign_is_deterministic_with_per_level_seeds():
    a = plan_campaign("dodge", 3, seed="s")
    assert a == plan_campaign("dodge", 3, seed="s")                  # reproducible
    assert a != plan_campaign("dodge", 3, seed="t")                 # seed matters
    assert plan_campaign("dodge", 3, seed=None) == plan_campaign("dodge", 3)  # None = plain
    # distinct per-level seeds -> the levels are not identical layouts
    plain = plan_campaign("dodge", 3)
    seeded = plan_campaign("dodge", 3, seed="x")
    assert plain["levels"][1]["plan"] != seeded["levels"][1]["plan"]


def test_campaign_level_count_clamped():
    assert plan_campaign("arena", 0)["level_count"] == 1
    assert plan_campaign("arena", 99)["level_count"] == 10


def test_unknown_game_type_falls_back_to_collectathon():
    assert plan_campaign("nonsense", 2)["game_type"] == "collectathon"


# --- the tool ---------------------------------------------------------------

def test_tool_returns_a_lean_view_without_full_plans():
    tool = {t.name: t for t in get_all_tools()}.get("unity_plan_campaign")
    assert tool is not None
    out = tool.fn("arena", 3)
    assert out["kind"] == "campaign" and out["level_count"] == 3
    # the lean view drops each level's full step plan (kept glanceable)
    assert all("plan" not in lv for lv in out["levels"])
    assert all({"level", "label", "count", "summary", "playable"} <= set(lv) for lv in out["levels"])


# --- intent routing ---------------------------------------------------------

@pytest.mark.parametrize("prompt,gt,levels", [
    ("arena kampanyasi kur", "arena", 3),
    ("3 seviyeli dodge oyunu", "dodge", 3),
    ("horde campaign yap", "horde", 3),
    ("5 seviyeli tower defense kampanyasi", "tower_defense", 5),
])
def test_campaign_intent_routes(prompt, gt, levels):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_plan_campaign", prompt
    assert step["kwargs"]["game_type"] == gt
    assert step["kwargs"]["levels"] == levels


def test_campaign_does_not_steal_build_or_variations():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    assert tool("arena oyunu kur") == "unity_build_simple_game"      # plain build unaffected
    assert tool("arena varyasyonlari goster") == "unity_game_variations"
    assert tool("dodge oyunu yap") == "unity_build_simple_game"
