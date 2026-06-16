"""P7 (cycle 35): game variations — same type, several difficulties, pure.

plan_game_variations builds the same game at different counts (easy/medium/hard)
and attaches a readiness summary to each. Every variation must be playable; the
difficulty must rise monotonically with count (more objects). Pure, no bridge.
"""
import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_game_variations, BLUEPRINTS, _difficulty_labels


def test_default_three_variations_easy_medium_hard():
    out = plan_game_variations("collectathon")
    assert out["ok"] is True and out["game_type"] == "collectathon"
    assert [v["label"] for v in out["variations"]] == ["easy", "medium", "hard"]
    assert [v["params"]["count"] for v in out["variations"]] == [3, 5, 8]


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_every_variation_is_playable(game_type):
    out = plan_game_variations(game_type)
    assert out["variations"]
    for v in out["variations"]:
        assert v["playable"] is True, f"{game_type}/{v['label']} not playable: {v['warnings']}"


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_every_variation_carries_a_coherent_design_critique(game_type):
    # the design critique rides along with each variation (consistent self-review), and
    # every shipped blueprint is coherent so the notes are empty
    out = plan_game_variations(game_type)
    for v in out["variations"]:
        assert "design_notes" in v and v["design_notes"] == []


def test_difficulty_is_monotonic_in_objects():
    out = plan_game_variations("chase", counts=[2, 4, 6, 9])
    counts = [v["params"]["count"] for v in out["variations"]]
    objects = [v["object_count"] for v in out["variations"]]
    assert counts == [2, 4, 6, 9]                          # sorted ascending
    assert objects == sorted(objects)                       # more enemies -> more objects
    assert len(set(objects)) == len(objects)                # strictly increasing


def test_counts_are_deduped_clamped_and_sorted():
    out = plan_game_variations("dodge", counts=[8, 3, 3, 0, 5])
    counts = [v["params"]["count"] for v in out["variations"]]
    assert counts == [1, 3, 5, 8]                           # 0->1 clamp, dup 3 removed, sorted


def test_unknown_game_type_falls_back_to_collectathon():
    out = plan_game_variations("nonsense")
    assert out["game_type"] == "collectathon"


def test_arena_size_is_recorded():
    out = plan_game_variations("survival", counts=[3], arena_size=30.0)
    assert out["variations"][0]["params"]["arena_size"] == 30.0


def test_difficulty_labels_presets():
    assert _difficulty_labels(1) == ["standard"]
    assert _difficulty_labels(2) == ["easy", "hard"]
    assert _difficulty_labels(3) == ["easy", "medium", "hard"]
    assert _difficulty_labels(5) == [f"level-{i + 1}" for i in range(5)]


def test_tool_is_pure_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)                 # must work with no bridge
    r = ut.unity_game_variations("platformer", counts="2,4,6")
    assert r["ok"] is True and r["game_type"] == "platformer"
    assert [v["params"]["count"] for v in r["variations"]] == [2, 4, 6]
    assert all(v["playable"] for v in r["variations"])


def test_tool_empty_counts_uses_default(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = ut.unity_game_variations("dodge")
    assert [v["params"]["count"] for v in r["variations"]] == [3, 5, 8]


def test_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_game_variations") is not None
