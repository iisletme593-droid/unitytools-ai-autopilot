"""P6 (cycle 10): LLM-free Unity fast-action executor.

run_unity_fast_action plans with plan_unity_fast_action then runs each step against
resolver-provided tools, streaming events — the Unity counterpart of chat_server's
Unreal fast-path. Tools resolve from the @tool registry (no hand-maintained map).
"""
from unitytools.core.game_studio_actions import run_unity_fast_action


def _recording_resolver(calls):
    def resolver(name):
        def fn(**kwargs):
            calls.append((name, kwargs))
            return {"ok": True}
        return fn
    return resolver


def test_executes_planned_steps_and_streams_events():
    calls = []
    events = []
    outcome = run_unity_fast_action(
        "once snapshot al sonra orman kur 30 agac",
        _recording_resolver(calls),
        emit=events.append,
    )
    assert outcome["engine"] == "unity"
    tools = [e["tool"] for e in outcome["executed"]]
    assert tools[0] == "unity_create_scene_snapshot"
    assert "unity_create_optimized_forest_scene" in tools
    assert outcome["ok"] is True
    assert {e["type"] for e in events} >= {"thinking", "tool_call", "tool_result"}
    # the forest step received the parsed count
    assert ("unity_create_optimized_forest_scene", {"tree_count": 30, "clear_scene": True}) in calls


def test_no_plan_returns_none():
    assert run_unity_fast_action("merhaba nasilsin", lambda n: None) is None


def test_unregistered_tool_is_skipped_not_crashed():
    outcome = run_unity_fast_action("sahneyi listele", lambda n: None)
    assert outcome is not None
    assert outcome["ran_count"] == 0
    assert outcome["executed"][0]["skipped"] is True
    assert outcome["ok"] is False


def test_tool_error_is_captured():
    def resolver(name):
        def boom(**kwargs):
            raise RuntimeError("kaboom")
        return boom
    outcome = run_unity_fast_action("sahneyi listele", resolver)
    assert outcome["executed"][0]["ok"] is False
    assert outcome["ok"] is False


def test_registry_resolver_finds_real_tools():
    import unitytools.tools  # noqa: F401 - register
    from unitytools.core.tool_registry import get_tool
    for name in ("unity_get_scene_catalog", "unity_create_optimized_forest_scene", "unity_run_visual_qa"):
        spec = get_tool(name)
        assert spec is not None and callable(spec.fn), name
