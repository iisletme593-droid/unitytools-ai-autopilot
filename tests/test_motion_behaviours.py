"""P7 (cycle 30): fill the remaining scripted-behaviour templates.

bob / bounce / patrol / follow / chase / orbit / wander were declared in
NEEDS_SCRIPT but had no MonoBehaviour source. Each now generates a compilable,
pure-ASCII, balanced template. Pure + deterministic; no recompile triggered.
"""
import pytest

from unitytools.core.gameplay import (
    generate_behaviour_script,
    normalize_behaviour,
    NEEDS_SCRIPT,
    _SCRIPT_TEMPLATES,
)

NEWLY_TEMPLATED = ["bob", "bounce", "patrol", "follow", "chase", "orbit", "wander"]


def test_no_behaviour_is_left_without_a_template():
    """Every behaviour we declare as needing a script must now produce one."""
    missing = sorted(b for b in NEEDS_SCRIPT if b not in _SCRIPT_TEMPLATES)
    assert missing == [], f"declared-but-unimplemented behaviours: {missing}"


@pytest.mark.parametrize("behaviour", NEWLY_TEMPLATED)
def test_generates_compilable_ascii_source(behaviour):
    s = generate_behaviour_script(behaviour)
    assert s["ok"] is True
    src = s["source"]
    assert src.count("{") == src.count("}")            # balanced braces
    assert src.count("(") == src.count(")")            # balanced parens
    assert all(ord(c) < 128 for c in src), "generated C# must be pure ASCII"
    assert "MonoBehaviour" in src
    assert "__" not in src                              # every placeholder substituted


def test_each_class_name_is_distinct_and_expected():
    expected = {
        "bob": "AutopilotBob",
        "bounce": "AutopilotBounce",
        "patrol": "AutopilotPatrol",
        "follow": "AutopilotFollower",
        "chase": "AutopilotFollower",   # chase is an alias of follow
        "orbit": "AutopilotOrbit",
        "wander": "AutopilotWander",
    }
    for b, cls in expected.items():
        assert generate_behaviour_script(b)["class_name"] == cls


def test_bob_uses_sine_around_start():
    src = generate_behaviour_script("bob")["source"]
    assert "Mathf.Sin(Time.time" in src
    assert "startPos" in src


def test_patrol_pingpongs_between_two_points():
    src = generate_behaviour_script("patrol")["source"]
    assert "Mathf.PingPong" in src
    assert "pointA" in src and "pointB" in src


def test_follower_chases_the_player_tag_safely():
    src = generate_behaviour_script("follow")["source"]
    assert 'FindWithTag("Player")' in src
    assert "Vector3.MoveTowards" in src
    assert "if (target == null) return;" in src        # no-op when no player


def test_turkish_aliases_resolve_to_new_templates():
    assert normalize_behaviour("devriye") == "patrol"
    assert normalize_behaviour("takip") == "follow"
    assert normalize_behaviour("zipla") == "bounce"
    for alias in ("devriye", "takip", "zipla"):
        assert generate_behaviour_script(alias)["ok"] is True
