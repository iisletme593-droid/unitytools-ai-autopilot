"""P14 (cycle 115): the behaviour reference -- a code-derived GLOSSARY of every scripted
gameplay building block (the 8th self-awareness surface, the first at BEHAVIOUR granularity).

build_behaviour_reference() lists, per canonical behaviour grouped by category, its generated
MonoBehaviour class (read live from _SCRIPT_TEMPLATES), a one-line purpose (_BEHAVIOUR_PURPOSES),
and which game types use it (code-derived). The class + used-by columns are derived so they never
drift; the purpose key set is drift-guarded against the category list so no behaviour is omitted.
"""
import pytest

import unitytools.tools  # noqa: F401 - register @tools
from unitytools.core.game_qa import (
    build_behaviour_reference, _BEHAVIOUR_PURPOSES, _BEHAVIOUR_CATEGORIES, _games_with_behaviour)
from unitytools.core.gameplay import _SCRIPT_TEMPLATES
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools


def _all_canonical():
    return {b for behs in _BEHAVIOUR_CATEGORIES.values() for b in behs}


# --- drift guards -----------------------------------------------------------

def test_every_categorized_behaviour_has_a_purpose_and_no_extras():
    # the glossary can never silently omit (or invent) a building block
    assert set(_BEHAVIOUR_PURPOSES) == _all_canonical()


def test_every_canonical_behaviour_has_a_live_template():
    # each canonical behaviour resolves to a real generated MonoBehaviour class
    for b in _all_canonical():
        assert b in _SCRIPT_TEMPLATES, b
        assert _SCRIPT_TEMPLATES[b][0].startswith("Autopilot")


# --- the rendered reference -------------------------------------------------

def test_reference_is_ascii_and_lists_every_behaviour_with_class():
    text = build_behaviour_reference()
    assert all(ord(c) < 128 for c in text)
    for b in _all_canonical():
        cls = _SCRIPT_TEMPLATES[b][0]
        assert f"**{b}**" in text, b
        assert f"`{cls}`" in text, cls
    # every category heading is present
    for category in _BEHAVIOUR_CATEGORIES:
        assert f"## {category}" in text


def test_reference_shows_code_derived_used_by_games():
    text = build_behaviour_reference()
    # a behaviour used by real blueprints shows them; a decor-only one is flagged as such
    assert _games_with_behaviour("collectible")            # sanity: collectible is used by games
    for g in _games_with_behaviour("lockgoal"):
        assert g == "keydoor"                              # lockgoal is unique to keydoor
    assert "[used by:" in text and "keydoor" in text


def test_purposes_are_nonempty_one_liners():
    for b, purpose in _BEHAVIOUR_PURPOSES.items():
        assert purpose and "\n" not in purpose and all(ord(c) < 128 for c in purpose), b


# --- tool + intent ----------------------------------------------------------

def test_tool_is_registered_and_pure():
    tool = {t.name: t for t in get_all_tools()}.get("unity_behaviour_reference")
    assert tool is not None
    out = tool.fn()
    assert out["ok"] is True
    assert out["behaviour_count"] == len(_all_canonical())
    assert "Behaviour Reference" in out["reference"]


@pytest.mark.parametrize("prompt", [
    "davranis sozlugu ver", "hangi davranislar var", "behaviour reference goster",
    "behaviour glossary", "list behaviours", "tum davranislar neler",
])
def test_behaviour_reference_intent_routes(prompt):
    step = plan_unity_fast_action(prompt)["steps"][0]
    assert step["tool"] == "unity_behaviour_reference", prompt


def test_behaviour_reference_does_not_steal_game_catalog_or_composer_report():
    def tool(p):
        return plan_unity_fast_action(p)["steps"][0]["tool"]
    # the GAME catalog and COMPOSER-ELEMENT report keep their own intents
    assert tool("hangi oyunlar yapabilirsin") == "unity_game_catalog"
    assert tool("neler yapabilirsin") == "unity_game_catalog"
    assert tool("ne tarif edebilirim") == "unity_composer_report"
    assert tool("hangi ogeler var") == "unity_composer_report"
    # and it does not grab a build
    assert tool("arena oyunu kur") == "unity_build_simple_game"
