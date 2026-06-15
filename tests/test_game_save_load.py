"""P8 (cycle 41): save / load games to disk — safely.

save_plan_to_file / load_plan_from_file write a game's plan as JSON under a
contained directory and read it back with no loss. Names are sanitized to a slug
and the path is re-guarded with safe_contained_path, so no name can escape the
games root. Saving never touches the scene; loading only returns a plan.
"""
import json

import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_game
from unitytools.core.game_io import (
    sanitize_game_name,
    save_plan_to_file,
    load_plan_from_file,
    list_saved_games,
)


# --- pure: name sanitization (path-traversal defense, no I/O) ---------------

@pytest.mark.parametrize("raw,expected", [
    ("my game", "my_game"),
    ("Dodge-1", "Dodge-1"),
    ("level_2", "level_2"),
    ("../../etc/passwd", "etc_passwd"),
    ("a/b/c", "a_b_c"),
    ("..", None),               # nothing safe -> ValueError
    ("/", None),
    ("...", None),
])
def test_sanitize_game_name(raw, expected):
    if expected is None:
        with pytest.raises(ValueError):
            sanitize_game_name(raw)
    else:
        assert sanitize_game_name(raw) == expected


def test_sanitize_caps_length():
    assert len(sanitize_game_name("x" * 200)) == 64


# --- disk round-trip (tmp_path) ---------------------------------------------

def test_save_then_load_round_trips(tmp_path):
    plan = plan_game("chase", 4)
    res = save_plan_to_file(plan, "my chase", root=tmp_path)
    assert res["ok"] is True and res["name"] == "my_chase"
    assert (tmp_path / "my_chase.json").is_file()
    assert load_plan_from_file("my chase", root=tmp_path) == plan


def test_saved_file_is_valid_envelope_json(tmp_path):
    save_plan_to_file(plan_game("dodge", 3), "d1", root=tmp_path)
    env = json.loads((tmp_path / "d1.json").read_text(encoding="utf-8"))
    assert env["schema"] == "unitytools.game_plan" and env["kind"] == "game"


def test_list_saved_games(tmp_path):
    assert list_saved_games(root=tmp_path) == []
    save_plan_to_file(plan_game("dodge", 3), "bravo", root=tmp_path)
    save_plan_to_file(plan_game("chase", 3), "alpha", root=tmp_path)
    assert list_saved_games(root=tmp_path) == ["alpha", "bravo"]   # sorted


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_plan_from_file("nope", root=tmp_path)


def test_traversal_name_cannot_escape_root(tmp_path):
    # a malicious name is sanitized to a slug that lands INSIDE the root
    res = save_plan_to_file(plan_game("dodge", 2), "../../escape", root=tmp_path)
    written = (tmp_path / (res["name"] + ".json"))
    assert written.is_file()
    assert written.resolve().parent == tmp_path.resolve()          # never outside
    # and no file leaked to the parent
    assert not (tmp_path.parent / "escape.json").exists()


# --- tools (env-pointed games dir) ------------------------------------------

def test_tools_save_list_load(monkeypatch, tmp_path):
    monkeypatch.setenv("UNITYTOOLS_GAMES_DIR", str(tmp_path))
    monkeypatch.setattr(ut, "_UNITY", None)                        # pure, no bridge

    saved = ut.unity_save_game("platformer", name="tower", collectible_count=4)
    assert saved["ok"] is True and saved["name"] == "tower"

    listed = ut.unity_list_saved_games()
    assert listed["ok"] is True and listed["games"] == ["tower"] and listed["count"] == 1

    loaded = ut.unity_load_game("tower")
    assert loaded["ok"] is True and loaded["game"] == "platformer"
    assert loaded["plan"] == plan_game("platformer", 4)            # load returns the plan, unbuilt


def test_tool_load_missing_returns_error(monkeypatch, tmp_path):
    monkeypatch.setenv("UNITYTOOLS_GAMES_DIR", str(tmp_path))
    r = ut.unity_load_game("ghost")
    assert r["ok"] is False and "error" in r


def test_save_load_tools_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    for name in ("unity_save_game", "unity_load_game", "unity_list_saved_games"):
        assert get_tool(name) is not None
