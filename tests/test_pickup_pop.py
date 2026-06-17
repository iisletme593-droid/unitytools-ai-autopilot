"""Cycle 106: pickup pop -- a UNIVERSAL feel/juice upgrade on the collect moment.

The existing `collectible` behaviour (AutopilotCollectible) now scores IMMEDIATELY on pickup
then plays a short scale-up "pop" before destroying itself. It is a pure source enrichment --
the behaviour name/class is unchanged, so every blueprint that uses collectibles (collectathon
/ chase / collector_race + the composer) gets the juice for free with ZERO plan/structure
changes. Deterministic (only Time), and the `collected` guard keeps scoring exactly once.
"""
from unitytools.core.gameplay import generate_behaviour_script
from unitytools.core.game_blueprint import plan_game, group_execution_plan, BLUEPRINTS
from unitytools.core.game_qa import studio_health


def _src():
    return generate_behaviour_script("collectible")["source"]


# --- the pop is present and correct -----------------------------------------

def test_collectible_pops_before_it_is_destroyed():
    src = _src()
    # a scale-up pop driven by Time, plus the public knobs
    assert "popTime" in src and "popScale" in src
    assert "transform.localScale" in src and "baseScale" in src
    assert "Time.deltaTime" in src
    # the pop runs in Update; Destroy happens when the pop finishes (not instantly on trigger)
    assert "void Update()" in src
    assert "Destroy(gameObject)" in src


def test_scoring_is_immediate_and_fires_exactly_once():
    src = _src()
    # the score is sent the instant you touch it (not after the pop), guarded so it fires once
    assert 'SendMessage("AddScore"' in src
    assert "collected = true" in src
    assert "if (!collected" in src            # the once-only guard


def test_still_decoupled_and_deterministic_and_ascii():
    src = _src()
    assert "AutopilotScore." not in src and "GetComponent<AutopilotScore>" not in src
    assert all(ord(c) < 128 for c in src)
    assert src.count("{") == src.count("}") and src.count("(") == src.count(")")
    assert "__" not in src
    for forbidden in ("Random.", "Math.random", "DateTime"):
        assert forbidden not in src


# --- it changes the SOURCE only, never the plan structure -------------------

def test_no_blueprint_structure_changed():
    # the behaviour name is unchanged, so the grouped script/attachment sets are identical
    for gt in ("collectathon", "chase", "collector_race"):
        grouped = group_execution_plan(plan_game(gt, 5)["steps"])
        assert "collectible" in grouped["script_behaviours"], gt
    # and the whole catalog is still clean
    h = studio_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"] and h["flagged"] == []
