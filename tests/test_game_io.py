"""P8 (cycle 40): game save/load — serialize a plan to JSON and back.

serialize_plan/deserialize_plan round-trip any blueprint or decor plan through a
versioned JSON envelope with NO loss, so a game can be persisted and replayed.
Pure string<->dict; no disk, no bridge.
"""
import json

import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_game, plan_ambient_decor, BLUEPRINTS
from unitytools.core.game_io import serialize_plan, deserialize_plan, plan_metadata, SCHEMA, SCHEMA_VERSION


@pytest.mark.parametrize("game_type", sorted(BLUEPRINTS))
def test_round_trip_every_blueprint(game_type):
    plan = plan_game(game_type, 5)
    restored = deserialize_plan(serialize_plan(plan))
    assert restored == plan                          # exact round-trip, no loss


def test_round_trip_decor_plan():
    plan = plan_ambient_decor(8)
    assert deserialize_plan(serialize_plan(plan)) == plan


def test_envelope_is_versioned_and_typed():
    env = json.loads(serialize_plan(plan_game("dodge", 4)))
    assert env["schema"] == SCHEMA
    assert env["version"] == SCHEMA_VERSION
    assert env["kind"] == "game"
    assert env["name"] == "dodge"
    assert env["step_count"] == len(env["plan"]["steps"])


def test_decor_envelope_kind():
    env = json.loads(serialize_plan(plan_ambient_decor(4)))
    assert env["kind"] == "decor" and env["name"] == "ambient"


def test_plan_metadata_without_full_plan():
    meta = plan_metadata(serialize_plan(plan_game("chase", 6)))
    assert meta["kind"] == "game" and meta["name"] == "chase"
    assert meta["step_count"] > 0 and "plan" not in meta


def test_pretty_is_valid_and_round_trips():
    text = serialize_plan(plan_game("survival", 3), pretty=True)
    assert "\n" in text                              # indented
    assert deserialize_plan(text) == plan_game("survival", 3)


def test_serialize_rejects_non_plan():
    with pytest.raises(ValueError):
        serialize_plan({"not": "a plan"})            # no steps
    with pytest.raises(ValueError):
        serialize_plan("nope")


def test_deserialize_rejects_bad_input():
    with pytest.raises(ValueError):
        deserialize_plan("{ not json")
    with pytest.raises(ValueError):
        deserialize_plan(json.dumps({"schema": "something.else", "plan": {}}))
    with pytest.raises(ValueError):
        deserialize_plan(json.dumps({"schema": SCHEMA, "version": 1, "plan": {"no": "steps"}}))


def test_deserialize_rejects_future_version():
    future = json.dumps({"schema": SCHEMA, "version": SCHEMA_VERSION + 1,
                         "plan": {"game": "x", "steps": []}})
    with pytest.raises(ValueError):
        deserialize_plan(future)


def test_export_tool_is_pure_and_round_trips(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)          # must work with no bridge
    r = ut.unity_export_game("platformer", 4)
    assert r["ok"] is True and r["game_type"] == "platformer"
    restored = deserialize_plan(r["json"])
    assert restored == plan_game("platformer", 4)


def test_export_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_export_game") is not None
