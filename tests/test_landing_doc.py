"""Cycle 39: the GAME_STUDIO.md landing page must not reference anything fake.

Same guarantee as test_games_doc but for the one-page entry point: every game
type and every unity_* tool it names must really exist in the live catalog /
registry, and it must link to the sibling docs.
"""
import pathlib
import re

import unitytools.tools  # noqa: F401 - register all tools
from unitytools.core.tool_registry import get_all_tools
from unitytools.core.game_blueprint import BLUEPRINTS

DOC = pathlib.Path(__file__).resolve().parents[1] / "docs" / "GAME_STUDIO.md"
TEXT = DOC.read_text(encoding="utf-8")
REGISTERED = {t.name for t in get_all_tools()}


def test_landing_doc_exists_and_nonempty():
    assert TEXT.strip(), "GAME_STUDIO.md is empty"


def test_every_unity_tool_named_is_registered():
    referenced = set(re.findall(r"(?<![a-z_])unity_[a-z_]+", TEXT))
    missing = sorted(t for t in referenced if t not in REGISTERED)
    assert missing == [], f"landing doc references unregistered tools: {missing}"


def test_every_blueprint_is_listed():
    for gt in BLUEPRINTS:
        assert gt in TEXT, f"landing doc missing game type {gt}"


def test_core_tools_are_mentioned():
    for tool in ("unity_build_simple_game", "unity_assess_game",
                 "unity_game_variations", "unity_game_catalog", "unity_animate_group"):
        assert tool in TEXT, f"landing doc should mention {tool}"


def test_links_to_sibling_docs():
    for sibling in ("GAME_STUDIO_GAMES.md", "GAME_STUDIO_TOOLS.md",
                    "GAME_STUDIO_ROADMAP.md", "GAME_STUDIO_PROGRESS.md"):
        assert sibling in TEXT, f"landing doc should link to {sibling}"
