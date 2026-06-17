"""P14 (cycle 96): the game showcase -- a code-derived, SELF-VERIFYING discovery gallery.

For every game type, build_game_showcase() pairs a curated example NL prompt with a pitch
and the object count; showcase_routing() checks (live) that each example actually routes to
unity_build_simple_game for that game type. So the showcase is the first artifact that
guards the WHOLE NL-intent layer per game type (break any detection and this goes red),
and a user-facing "say this -> get this game" gallery. Exposed as the unity_game_showcase
tool and the "ornek oyunlar / show me examples" intent.
"""
import pytest

import unitytools.tools  # noqa: F401 - register all @tools
from unitytools.core.game_qa import build_game_showcase, showcase_routing, _GAME_EXAMPLES
from unitytools.core.game_blueprint import BLUEPRINTS
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools


# --- the example map + routing self-check -----------------------------------

def test_every_game_type_has_an_example():
    # drift guard: a new blueprint forces an example (prompt + pitch) here
    assert set(_GAME_EXAMPLES) == set(BLUEPRINTS), set(BLUEPRINTS) ^ set(_GAME_EXAMPLES)
    for gt, (prompt, pitch) in _GAME_EXAMPLES.items():
        assert prompt.strip() and pitch.strip(), gt


def test_every_example_routes_to_its_own_build():
    # the heart of it: each curated example must plan unity_build_simple_game for its type
    route = showcase_routing()
    assert route["all_route"] is True
    broken = [(r["game_type"], r["prompt"], r["routes_to"]) for r in route["rows"] if not r["builds"]]
    assert broken == [], broken
    assert len(route["rows"]) == len(BLUEPRINTS)


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_each_examples_prompt_builds_that_type(game_type):
    prompt = _GAME_EXAMPLES[game_type][0]
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_build_simple_game", (game_type, prompt, step)
    assert step["kwargs"]["game_type"] == game_type, (game_type, prompt)


# --- the rendered showcase --------------------------------------------------

def test_showcase_lists_every_type_and_its_example():
    text = build_game_showcase()
    for gt, (prompt, _pitch) in _GAME_EXAMPLES.items():
        assert f"`{gt}`" in text, gt
        assert prompt in text, prompt
    assert f"## {len(BLUEPRINTS)} games" in text
    assert "all routing OK" in text                     # the live self-check passed


def test_showcase_is_pure_ascii():
    assert all(ord(c) < 128 for c in build_game_showcase())


def test_showcase_grows_when_a_game_type_is_added(monkeypatch):
    # drift proof: a fake blueprint with no example shows up as a non-routing row, and the
    # count grows -- so the showcase can never silently omit a game type
    from unitytools.core import game_qa, game_blueprint
    fake = dict(game_blueprint.BLUEPRINTS)
    fake["zzztest"] = lambda count=5: game_blueprint.plan_collectathon_game(count)
    monkeypatch.setattr(game_blueprint, "BLUEPRINTS", fake)
    monkeypatch.setattr(game_qa, "BLUEPRINTS", fake)
    route = showcase_routing()
    assert any(r["game_type"] == "zzztest" for r in route["rows"])
    assert len(route["rows"]) == len(fake)


# --- the tool + intent ------------------------------------------------------

def test_tool_is_registered_and_self_checks():
    tool = {t.name: t for t in get_all_tools()}.get("unity_game_showcase")
    assert tool is not None
    out = tool.fn()
    assert out["ok"] is True and out["all_route"] is True
    assert "Game Showcase" in out["showcase"]


@pytest.mark.parametrize("prompt", [
    "ornek oyunlar goster", "ornek goster", "show me examples", "game examples", "example games",
])
def test_showcase_intent_routes(prompt):
    assert plan_unity_fast_action(prompt)["steps"][0]["tool"] == "unity_game_showcase", prompt


def test_showcase_does_not_steal_catalog_report_or_build():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    # the lighter catalog, the studio report, and a real build are all unaffected
    assert tool("hangi oyunlar yapabilirsin") == "unity_game_catalog"
    assert tool("studio raporu ver") == "unity_studio_report"
    assert tool("arena oyunu kur") == "unity_build_simple_game"
    assert tool("neler yapabilirsin") == "unity_game_catalog"
