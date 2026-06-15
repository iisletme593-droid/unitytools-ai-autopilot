"""P7 (cycle 37): game catalog — the studio's one-glance "what can I make?" report.

summarize_catalog walks every blueprint, plans + assesses each, and returns a
single summary: per-game readiness plus the full behaviour set. Pure, no bridge.
The NL intent ("hangi oyunlar / what games") routes to unity_game_catalog, while
bare "katalog" (scene catalog) is left alone.
"""
import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import BLUEPRINTS
from unitytools.core.game_qa import summarize_catalog
from unitytools.core.game_studio_actions import plan_unity_fast_action


def test_catalog_lists_every_blueprint():
    cat = summarize_catalog()
    assert cat["ok"] is True
    assert cat["game_count"] == len(BLUEPRINTS)
    assert {g["game_type"] for g in cat["games"]} == set(BLUEPRINTS)


def test_all_games_are_playable():
    cat = summarize_catalog()
    assert cat["all_playable"] is True
    assert all(g["playable"] for g in cat["games"])


def test_each_game_entry_has_expected_fields():
    cat = summarize_catalog()
    for g in cat["games"]:
        assert set(g) >= {"game_type", "summary", "object_count", "unique_scripts",
                          "playable", "has_player", "has_goal", "has_score", "warnings"}
        assert g["object_count"] > 0
        assert g["has_player"] is True            # every game has a player


def test_catalog_aggregates_unique_behaviours():
    cat = summarize_catalog()
    # the union of behaviours across all games — player/goal must be in there
    assert "player" in cat["unique_behaviours"]
    assert "goal" in cat["unique_behaviours"]
    assert cat["behaviour_count"] == len(cat["unique_behaviours"])
    assert cat["behaviour_count"] >= 6            # at least player/goal/score/collectible/killzone/follow...


def test_games_are_sorted_for_stable_output():
    cat = summarize_catalog()
    types = [g["game_type"] for g in cat["games"]]
    assert types == sorted(types)


@pytest.mark.parametrize("prompt", [
    "oyun katalogu goster",
    "hangi oyunlar yapabilirsin",
    "neler yapabilirsin",
    "what games can you make",
    "list games",
    "oyun turleri neler",
])
def test_catalog_intent_routes_to_catalog(prompt):
    assert plan_unity_fast_action(prompt)["steps"][0]["tool"] == "unity_game_catalog", prompt


def test_scene_catalog_is_not_hijacked():
    assert plan_unity_fast_action("sahne katalogu cikar")["steps"][0]["tool"] == "unity_get_scene_catalog"
    assert plan_unity_fast_action("katalog")["steps"][0]["tool"] == "unity_get_scene_catalog"


def test_tool_is_pure_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_game_catalog()
    assert r["ok"] is True and r["game_count"] == len(BLUEPRINTS)
    assert r["all_playable"] is True


def test_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_game_catalog") is not None
