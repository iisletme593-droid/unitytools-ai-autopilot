"""Cycle 27: GAME_STUDIO_GAMES.md must not reference anything that doesn't exist.

Guards the docs against phantom tool/behaviour/game names by checking every
reference against the live registry and catalog.
"""
import pathlib
import re

import unitytools.tools  # noqa: F401 - register all tools
from unitytools.core.tool_registry import get_all_tools
from unitytools.core.game_blueprint import BLUEPRINTS
from unitytools.core.gameplay import GAMEPLAY_BEHAVIOURS, generate_behaviour_script

DOC = pathlib.Path(__file__).resolve().parents[1] / "docs" / "GAME_STUDIO_GAMES.md"
TEXT = DOC.read_text(encoding="utf-8")
REGISTERED = {t.name for t in get_all_tools()}


def test_every_unity_tool_in_doc_is_registered():
    # (?<![a-z_]) so we don't match the "unity_..." inside "plan_unity_fast_action"
    referenced = set(re.findall(r"(?<![a-z_])unity_[a-z_]+", TEXT))
    missing = sorted(t for t in referenced if t not in REGISTERED)
    assert missing == [], f"doc references unregistered tools: {missing}"


def test_documented_game_types_exist():
    for gt in ("collectathon", "dodge", "survival", "platformer", "chase"):
        assert gt in TEXT
        assert gt in BLUEPRINTS


def test_documented_physics_behaviours_exist():
    for b in ("physics", "falling", "heavy", "floaty", "kinematic", "static_obstacle"):
        assert b in TEXT
        assert b in GAMEPLAY_BEHAVIOURS


def test_documented_scripted_behaviours_generate():
    for b in ("rotate", "move", "player", "collectible", "goal", "killzone", "spawner", "score",
              "bob", "bounce", "patrol", "follow", "chase", "orbit", "wander"):
        assert b in TEXT
        assert generate_behaviour_script(b)["ok"] is True
