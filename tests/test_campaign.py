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


def test_campaign_carries_a_self_audit():
    # a campaign self-reports its health like studio_health: every level valid + playable
    # + coherent, with per-campaign aggregate flags and a per-level `valid`
    camp = plan_campaign("arena", 3)
    assert camp["all_valid"] and camp["all_playable"] and camp["all_coherent"]
    for lv in camp["levels"]:
        assert lv["valid"] and lv["playable"] and lv["design_notes"] == []


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_every_game_types_campaign_audits_clean(game_type):
    camp = plan_campaign(game_type, 3)
    assert camp["all_valid"] and camp["all_playable"] and camp["all_coherent"]


def test_campaign_audit_flags_in_the_lean_tool_view():
    tool = {t.name: t for t in get_all_tools()}.get("unity_plan_campaign")
    out = tool.fn("hold", 3)
    # the lean view keeps the aggregate flags + each level's `valid` (drops only the plan)
    assert out["all_valid"] and out["all_playable"] and out["all_coherent"]
    assert all("valid" in lv and "plan" not in lv for lv in out["levels"])


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


# --- cycle 82: saving a whole campaign --------------------------------------

def test_campaign_levels_save_and_reload(tmp_path):
    from unitytools.core.game_io import (save_plan_to_file, load_plan_from_file,
                                         list_saved_games)
    camp = plan_campaign("arena", 3, seed="c")
    for lv in camp["levels"]:
        save_plan_to_file(lv["plan"], f"boss_L{lv['level']}", root=tmp_path)
    assert list_saved_games(root=tmp_path) == ["boss_L1", "boss_L2", "boss_L3"]
    l2 = load_plan_from_file("boss_L2", root=tmp_path)
    assert validate_plan(l2)["ok"] is True
    assert assess_game_readiness(l2)["playable"] is True
    assert l2 == camp["levels"][1]["plan"]          # exact reload of level 2


def test_save_campaign_tool_is_registered():
    assert {t.name for t in get_all_tools()} >= {"unity_save_campaign"}


@pytest.mark.parametrize("prompt,gt,name,levels", [
    ("arena kampanyasini boss olarak kaydet", "arena", "boss", 3),
    ("3 seviyeli dodge kampanyasini kaydet", "dodge", "dodge_campaign", 3),
    ("5 seviyeli horde kampanyasini zindan olarak kaydet", "horde", "zindan", 5),
])
def test_campaign_save_intent_routes(prompt, gt, name, levels):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_save_campaign", prompt
    assert step["kwargs"]["game_type"] == gt
    assert step["kwargs"]["name"] == name
    assert step["kwargs"]["levels"] == levels


def test_campaign_save_does_not_steal_other_saves():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    # a plain preset save, a composed save, and a bare named save are all unaffected
    assert tool("dodge oyununu kaydet") == "unity_save_game"
    assert tool("ozel oyunu boss olarak kaydet") == "unity_save_composed_game"
    assert tool("kaydet boss") == "unity_save_game"
    # and planning a campaign (no "kaydet") still plans, not saves
    assert tool("arena kampanyasi kur") == "unity_plan_campaign"
