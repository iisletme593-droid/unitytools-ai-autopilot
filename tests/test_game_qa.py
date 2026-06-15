"""P7 (cycle 33): game QA — pure, bridge-free readiness analysis.

assess_game_readiness reads a blueprint plan and reports object/behaviour counts
plus a playable verdict and warnings. Every game in BLUEPRINTS must come back
playable; decor (no player/goal) must come back not-playable with warnings.
"""
import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_game, plan_ambient_decor, BLUEPRINTS
from unitytools.core.game_qa import summarize_plan, assess_game_readiness


def test_summarize_counts_objects_and_behaviours():
    summary = summarize_plan(plan_game("collectathon", 3))
    # ground + player + 3 collectibles + goal = 6 objects (set_tag creates nothing)
    assert summary["object_count"] == 6
    bc = summary["behaviour_counts"]
    assert bc["player"] == 1 and bc["collectible"] == 3 and bc["goal"] == 1 and bc["score"] == 1


def test_physics_behaviours_are_counted_too():
    # platformer's solid platforms use the static_obstacle PHYSICS behaviour (a tool step)
    bc = summarize_plan(plan_game("platformer", 4))["behaviour_counts"]
    assert bc.get("static_obstacle") == 4


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_every_blueprint_is_playable(game_type):
    report = assess_game_readiness(plan_game(game_type, 4))
    assert report["ok"] is True
    assert report["has_player"] is True
    assert report["playable"] is True, f"{game_type} should be playable: {report['warnings']}"
    assert report["object_count"] > 0


def test_readiness_fields_for_collectathon():
    r = assess_game_readiness(plan_game("collectathon", 5))
    assert r["game"] == "collectathon"
    assert r["has_player"] and r["has_goal"] and r["has_score"]
    assert r["collectible_count"] == 5
    assert r["warnings"] == []                       # complete game, nothing missing


def test_survival_warns_about_missing_goal_but_still_playable():
    r = assess_game_readiness(plan_game("survival", 3))
    assert r["playable"] is True                      # player + spawners is playable
    assert r["has_goal"] is False
    assert any("no goal" in w for w in r["warnings"])


def test_chase_counts_hazards_and_collectibles():
    r = assess_game_readiness(plan_game("chase", 4))
    assert r["hazard_count"] == 4                     # 4 killzone enemies
    assert r["collectible_count"] == 4
    assert r["playable"] is True


def test_decor_is_not_a_playable_game():
    r = assess_game_readiness(plan_ambient_decor(8))
    assert r["has_player"] is False
    assert r["playable"] is False
    assert any("no player" in w for w in r["warnings"])
    assert any("not playable" in w for w in r["warnings"])


def test_empty_plan_warns():
    r = assess_game_readiness({"steps": []})
    assert r["object_count"] == 0
    assert r["playable"] is False
    assert any("empty scene" in w for w in r["warnings"])


def test_collectibles_without_score_warn():
    # a hand-built plan: player + collectible but no score HUD
    plan = {"game": "custom", "steps": [
        {"tool": "unity_create_primitive", "kwargs": {"type": "Cube", "name": "Player"}},
        {"script_behaviour": {"object": "Player", "behaviour": "player"}},
        {"tool": "unity_create_primitive", "kwargs": {"type": "Sphere", "name": "Coin"}},
        {"script_behaviour": {"object": "Coin", "behaviour": "collectible"}},
    ]}
    r = assess_game_readiness(plan)
    assert r["playable"] is True                      # player + collectible
    assert any("no score HUD" in w for w in r["warnings"])


def test_tool_is_pure_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)           # must work with no bridge
    r = ut.unity_assess_game("dodge", 5)
    assert r["ok"] is True and r["game"] == "dodge"
    assert r["playable"] is True
    assert "summary" in r


def test_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_assess_game") is not None
