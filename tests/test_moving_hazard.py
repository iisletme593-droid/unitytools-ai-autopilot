"""P14 (cycle 97): the moving-hazard composer element -- enriching the freeform composer
with a SLIDING obstacle (mover + killzone, the dodge game's threat) you can mix in.

The interesting part is the parser: "hareketli engel" (moving hazard) CONTAINS the
static-hazard trigger "engel", so it is extracted + stripped BEFORE the single-word
elements (parse_custom_spec -> _SPEC_PHRASE_ELEMENTS) -- "3 hareketli engel" is 3 moving
hazards and 0 static hazards, not a double-count. compose_custom_game gains a
`moving_hazard` count; compose_health audits it.
"""
import pytest

from unitytools.core.game_blueprint import compose_custom_game
from unitytools.core.game_qa import assess_game_readiness, compose_health
from unitytools.core.game_io import validate_plan
from unitytools.core.game_studio_actions import (
    parse_custom_spec, plan_unity_fast_action, build_composer_report, _SPEC_PHRASE_ELEMENTS)


def _beh_of(plan, obj):
    return {s["script_behaviour"]["behaviour"] for s in plan["steps"]
            if s.get("script_behaviour", {}).get("object") == obj}


# --- the composer element ---------------------------------------------------

def test_moving_hazard_is_a_sliding_killzone():
    plan = compose_custom_game(player=True, moving_hazard=4)
    # each moving hazard slides (mover) AND respawns the player on contact (killzone)
    assert _beh_of(plan, "MovingHazard_0") == {"mover", "killzone"}
    movers = [s["script_behaviour"]["object"] for s in plan["steps"]
              if s.get("script_behaviour", {}).get("behaviour") == "mover"]
    assert movers == [f"MovingHazard_{i}" for i in range(4)]
    assert plan["spec"]["moving_hazard"] == 4


def test_moving_hazard_is_a_pure_obstacle_no_manager():
    # like the static `hazard`, it pulls in NO win/lose manager and no health coupling
    plan = compose_custom_game(player=True, moving_hazard=3)
    assert not any(s.get("script_behaviour", {}).get("object") == "GameManager" for s in plan["steps"])
    assert "health" not in _beh_of(plan, "Player")


def test_moving_hazard_is_valid_playable_coherent():
    plan = compose_custom_game(player=True, moving_hazard=5)
    assert validate_plan(plan)["ok"] is True
    r = assess_game_readiness(plan)
    assert r["playable"] is True and r["has_player"] is True   # mover/killzone are interactive
    assert r["design_notes"] == []


def test_moving_hazard_count_clamped_and_deterministic():
    assert compose_custom_game(moving_hazard=99)["spec"]["moving_hazard"] == 30
    a = compose_custom_game(moving_hazard=5, seed="m")
    assert a == compose_custom_game(moving_hazard=5, seed="m")
    assert a != compose_custom_game(moving_hazard=5, seed="n")
    assert compose_custom_game(moving_hazard=5, seed=None) == compose_custom_game(moving_hazard=5)


# --- the parser: phrase extraction avoids the "engel" double-count ----------

def test_moving_hazard_does_not_double_count_static_hazard():
    spec = parse_custom_spec("ozel oyun 3 hareketli engel")
    assert spec["moving_hazard"] == 3 and spec["hazard"] == 0


def test_static_and_moving_hazards_coexist():
    spec = parse_custom_spec("ozel oyun 2 engel ve 4 hareketli engel")
    assert spec["hazard"] == 2 and spec["moving_hazard"] == 4


@pytest.mark.parametrize("text,count", [
    ("ozel oyun hareketli engel olsun", 1),       # bare phrase = 1
    ("ozel oyun iki hareketli engel", 2),          # number-word
    ("ozel oyun 5 moving hazard", 5),              # english
    ("ozel oyun kayan engel", 1),                  # synonym, still no static-hazard leak
])
def test_moving_hazard_count_parsing(text, count):
    spec = parse_custom_spec(text)
    assert spec["moving_hazard"] == count
    if "moving hazard" not in text:                # turkish phrases contain "engel"...
        assert spec["hazard"] == 0                 # ...which must NOT leak into static hazard


def test_plain_static_hazard_is_unchanged():
    # the single-word static hazard still parses exactly as before
    spec = parse_custom_spec("ozel oyun 6 engel")
    assert spec["hazard"] == 6 and spec["moving_hazard"] == 0


# --- the self-audit + report + intent ---------------------------------------

def test_compose_health_audits_moving_hazard_clean():
    h = compose_health()
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    assert h["flagged"] == []
    # the matrix actually includes a moving-hazard case
    assert any(c["spec"].get("moving_hazard") for c in h["cases"])


def test_composer_report_lists_the_phrase_element():
    rep = build_composer_report()
    assert all(ord(c) < 128 for c in rep)
    for key, words in _SPEC_PHRASE_ELEMENTS.items():
        assert f"**{key}**" in rep, key
        for w in words:
            assert w in rep, (key, w)


def test_moving_hazard_routes_keywordless_to_the_composer():
    step = plan_unity_fast_action("3 hareketli engel olan oyun yap")["steps"][0]
    assert step["tool"] == "unity_compose_game"
    assert step["kwargs"]["moving_hazard"] == 3
    assert step["kwargs"]["hazard"] == 0


def test_moving_hazard_does_not_disturb_static_hazard_routing():
    # a plain "engel" count still composes a static hazard, unaffected by the new element
    kw = plan_unity_fast_action("6 engel olan oyun yap")["steps"][0]["kwargs"]
    assert kw["hazard"] == 6 and kw["moving_hazard"] == 0
