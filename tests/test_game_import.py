"""P8 (cycle 43): import + build-from-plan — never trust external JSON.

validate_plan checks a (possibly hostile) plan structurally: every step must be a
WHITELISTED tool call with flat-primitive kwargs, or a real templated behaviour.
unity_import_game parses+validates without building; unity_build_loaded_game loads
a saved game, re-validates, and (only with execute=True) builds it.
"""
import json

import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_game, plan_ambient_decor, BLUEPRINTS
from unitytools.core.game_io import (
    validate_plan, serialize_plan, save_plan_to_file, ALLOWED_PLAN_TOOLS,
)


# --- validate_plan: accepts real plans --------------------------------------

@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_validate_accepts_every_blueprint(game_type):
    v = validate_plan(plan_game(game_type, 5))
    assert v["ok"] is True and v["step_count"] > 0


def test_validate_accepts_decor():
    assert validate_plan(plan_ambient_decor(6))["ok"] is True


# --- validate_plan: rejects hostile / malformed input -----------------------

def test_rejects_non_whitelisted_tool():
    plan = {"game": "x", "steps": [{"tool": "os_system", "kwargs": {"cmd": "rm -rf /"}}]}
    v = validate_plan(plan)
    assert v["ok"] is False and "not allowed" in v["error"] and v["index"] == 0


def test_rejects_unknown_behaviour():
    plan = {"game": "x", "steps": [{"script_behaviour": {"object": "P", "behaviour": "mind_control"}}]}
    v = validate_plan(plan)
    assert v["ok"] is False and "unknown behaviour" in v["error"]


def test_rejects_non_primitive_kwargs():
    plan = {"game": "x", "steps": [{"tool": "unity_create_primitive",
                                     "kwargs": {"type": "Cube", "evil": ["nested"]}}]}
    assert validate_plan(plan)["ok"] is False


def test_rejects_step_with_both_or_neither():
    both = {"steps": [{"tool": "unity_set_tag", "kwargs": {}, "script_behaviour": {"object": "a", "behaviour": "player"}}]}
    neither = {"steps": [{"foo": "bar"}]}
    assert validate_plan(both)["ok"] is False
    assert validate_plan(neither)["ok"] is False


def test_rejects_non_dict_and_missing_steps():
    assert validate_plan("not a plan")["ok"] is False
    assert validate_plan({"no": "steps"})["ok"] is False
    assert validate_plan({"steps": "nope"})["ok"] is False


def test_rejects_too_many_steps():
    huge = {"steps": [{"tool": "unity_set_tag", "kwargs": {}}] * 6000}
    assert validate_plan(huge, max_steps=5000)["ok"] is False


def test_whitelist_is_the_set_blueprints_use():
    assert ALLOWED_PLAN_TOOLS == {
        "unity_create_primitive", "unity_place_primitives",
        "unity_set_tag", "unity_add_gameplay_behaviour",
    }


# --- unity_import_game tool -------------------------------------------------

def test_import_valid_json(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    text = serialize_plan(plan_game("dodge", 4))
    r = ut.unity_import_game(text)
    assert r["ok"] is True and r["game"] == "dodge" and r["plan"] == plan_game("dodge", 4)


def test_import_rejects_bad_json():
    assert ut.unity_import_game("{ not json")["ok"] is False


def test_import_rejects_forged_tool():
    forged = json.dumps({"schema": "unitytools.game_plan", "version": 1,
                         "plan": {"game": "x", "steps": [{"tool": "danger", "kwargs": {}}]}})
    r = ut.unity_import_game(forged)
    assert r["ok"] is False and "invalid plan" in r["error"]


# --- unity_build_loaded_game (load -> validate -> build) --------------------

def test_build_loaded_dry_run_default(monkeypatch, tmp_path):
    monkeypatch.setenv("UNITYTOOLS_GAMES_DIR", str(tmp_path))
    monkeypatch.setattr(ut, "_UNITY", None)
    save_plan_to_file(plan_game("platformer", 4), "tower", root=tmp_path)
    r = ut.unity_build_loaded_game("tower")          # execute defaults False
    assert r["ok"] is True and r["dry_run"] is True and r["game"] == "platformer"


def test_build_loaded_missing_errors(monkeypatch, tmp_path):
    monkeypatch.setenv("UNITYTOOLS_GAMES_DIR", str(tmp_path))
    assert ut.unity_build_loaded_game("ghost")["ok"] is False


class _Bridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params=None, timeout=None):
        self.calls.append(method)
        if method == "get_editor_state":
            return {"is_compiling": False}
        return {"ok": True}


def test_build_loaded_executes_with_bridge(monkeypatch, tmp_path):
    monkeypatch.setenv("UNITYTOOLS_GAMES_DIR", str(tmp_path))
    fb = _Bridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    save_plan_to_file(plan_game("collectathon", 3), "c1", root=tmp_path)
    r = ut.unity_build_loaded_game("c1", execute=True)
    assert r["executed"] is True
    assert "create_primitive" in fb.calls and "add_component" in fb.calls


def test_import_and_build_tools_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    for name in ("unity_import_game", "unity_build_loaded_game"):
        assert get_tool(name) is not None
