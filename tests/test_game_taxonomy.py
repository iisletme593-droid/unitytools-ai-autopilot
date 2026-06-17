"""P14 (cycle 120): the game design taxonomy -- a code-derived GENRE classification (the 9th
self-awareness surface, a cross-cutting discovery lens).

game_genre_tags(plan) derives design-pattern tags (combat / ranged / collection / reach-the-exit /
stealth / puzzle / survival / timed / territory / escort / hazard-dodging) from a plan's behaviours.
build_game_taxonomy() groups the whole catalog by genre + lists each game's tags. Distinct from the
flat catalog: it answers "show me your TIMED games / your STEALTH games". Tags are derived, so it
never drifts; guarded so every game type earns at least one tag.
"""
import pytest

import unitytools.tools  # noqa: F401 - register @tools
from unitytools.core.game_qa import (
    game_genre_tags, build_game_taxonomy, _GENRE_TAGS)
from unitytools.core.game_blueprint import BLUEPRINTS, plan_game, compose_custom_game
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools


# --- the derivation ---------------------------------------------------------

def test_every_game_type_earns_at_least_one_tag():
    # the lens can never leave a game uncategorised
    for gt in BLUEPRINTS:
        tags = game_genre_tags(plan_game(gt, 4))
        assert tags, gt
        assert all(t in _GENRE_TAGS for t in tags), (gt, tags)


@pytest.mark.parametrize("game_type,expected", [
    ("collectathon", {"collection", "reach-the-exit"}),
    ("arena", {"combat"}),
    ("stealth", {"stealth", "reach-the-exit"}),
    ("puzzle", {"puzzle"}),
    ("speedrun", {"reach-the-exit", "hazard-dodging", "timed"}),
    ("frogger", {"reach-the-exit", "hazard-dodging"}),
    ("collector_race", {"collection", "timed"}),
    ("hold", {"territory"}),
    ("escort", {"escort"}),
    ("tower_defense", {"combat"}),
])
def test_tags_match_the_game_design(game_type, expected):
    tags = set(game_genre_tags(plan_game(game_type, 4)))
    assert expected <= tags, (game_type, tags)


def test_tags_work_on_a_composed_game_too():
    # a freeform composed game is classified just like a preset (derived from behaviours)
    tags = set(game_genre_tags(compose_custom_game(player=True, enemy=4, ranged=True)))
    assert "combat" in tags and "ranged" in tags


# --- the rendered taxonomy --------------------------------------------------

def test_taxonomy_is_ascii_and_groups_by_genre():
    text = build_game_taxonomy()
    assert all(ord(c) < 128 for c in text)
    assert "## By genre" in text and "## Each game's tags" in text
    # every game appears, and every genre that any game has is shown
    for gt in BLUEPRINTS:
        assert f"`{gt}`" in text
    for tag in _GENRE_TAGS:
        if any(tag in game_genre_tags(plan_game(gt, 4)) for gt in BLUEPRINTS):
            assert f"**{tag}**" in text, tag


def test_timed_genre_collects_the_clock_games():
    from unitytools.core.game_qa import build_game_taxonomy as _b  # noqa: F401
    timed = {gt for gt in BLUEPRINTS if "timed" in game_genre_tags(plan_game(gt, 4))}
    # the clock games cluster under "timed"
    assert {"speedrun", "collector_race", "time_survival"} <= timed


# --- tool + intent ----------------------------------------------------------

def test_tool_is_registered_and_pure():
    tool = {t.name: t for t in get_all_tools()}.get("unity_game_taxonomy")
    assert tool is not None
    out = tool.fn()
    assert out["ok"] is True
    assert "Design Taxonomy" in out["taxonomy"]
    assert set(out["genres"]) == set(_GENRE_TAGS)


@pytest.mark.parametrize("prompt", [
    "oyun taksonomisi ver", "turleri grupla", "game taxonomy goster",
    "oyunlari genre olarak grupla", "tasarim deseni ozeti",
])
def test_taxonomy_intent_routes(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_game_taxonomy", prompt


def test_taxonomy_does_not_steal_the_game_catalog_or_behaviour_reference():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    assert tool("hangi oyunlar yapabilirsin") == "unity_game_catalog"
    assert tool("oyun turleri neler") == "unity_game_catalog"
    assert tool("davranis sozlugu ver") == "unity_behaviour_reference"
    assert tool("arena oyunu kur") == "unity_build_simple_game"
