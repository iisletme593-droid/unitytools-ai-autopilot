"""P3 (cycle 14): props/characters/weapons asset-finders now feed the ContextManager.

Before this, _update_context_from_tools only wired tree/rock finders, so prop and
character context stayed empty even though ContextManager.update_assets supported
them. Tested by calling the (unbound) method with a lightweight fake self — no need
to construct the full DualAgentOrchestrator.
"""
from types import SimpleNamespace

from unitytools.core.context_manager import ContextManager
from unitytools.core.dual_agent import DualAgentOrchestrator, ASSET_FINDER_CATEGORIES


def _feed(calls):
    ctx = ContextManager()
    DualAgentOrchestrator._update_context_from_tools(SimpleNamespace(context=ctx), calls)
    return ctx


def _find(tool, *paths, ok=True):
    return {"name": tool, "ok": ok, "result": {"results": [{"path": p} for p in paths]}}


def test_mapping_covers_props_and_characters():
    assert ASSET_FINDER_CATEGORIES["unity_find_prop_assets"] == "props"
    assert ASSET_FINDER_CATEGORIES["unity_find_character_assets"] == "characters"


def test_props_and_characters_feed_context():
    ctx = _feed([
        _find("unity_find_prop_assets", "Assets/Props/barrel.fbx"),
        _find("unity_find_character_assets", "Assets/Chars/hero.fbx"),
    ])
    assert ctx.assets.props == ["Assets/Props/barrel.fbx"]
    assert ctx.assets.characters == ["Assets/Chars/hero.fbx"]
    assert ctx.assets.total_assets == 2


def test_weapons_grouped_as_props():
    ctx = _feed([_find("unity_find_weapon_assets", "Assets/W/sword.fbx")])
    assert "Assets/W/sword.fbx" in ctx.assets.props


def test_trees_rocks_still_work():
    ctx = _feed([
        _find("unity_find_tree_assets", "Assets/T/pine.fbx"),
        _find("unity_find_rock_assets", "Assets/R/boulder.fbx"),
    ])
    assert ctx.assets.trees == ["Assets/T/pine.fbx"]
    assert ctx.assets.rocks == ["Assets/R/boulder.fbx"]


def test_failed_finder_does_not_feed():
    ctx = _feed([_find("unity_find_prop_assets", "Assets/x.fbx", ok=False)])
    assert ctx.assets.props == []
