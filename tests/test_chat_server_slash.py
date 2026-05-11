"""Phase 67 tests: chat-server slash-command parity.

The Unity Editor's chat panel speaks the same newline-JSON protocol the
REPL uses. Phase 59-66 added /scaffold, /sync, /build, etc., to the REPL
via chat_commands.dispatch — but the chat-server bypassed all of that and
sent every user_message straight to the LLM.

Phase 67 wires the same deterministic dispatcher into the chat-server so
Unity Editor users get identical slash-command surface. This file proves:
- Slash commands are recognised
- They emit tool_call + tool_result + assistant_text + assistant_done
- Unknown slash commands return a friendly error (no LLM call)
- Non-slash messages still flow through the orchestrator path unchanged
- Türkçe aliases work (/yardım, /denetim, ...)
- Bridge-aware commands (/build) see the bridge via DispatchContext
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.core.chat_server import ChatServer
from unitytools.core.config import Config
from unitytools.studio import StudioPaths, StudioState, init_studio_tools


# ─────────────────────────────────────── helpers


class _Capture:
    """Collect every send(payload) call from _handle_line."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def __call__(self, payload: dict) -> None:
        # Round-trip through JSON to catch any non-serializable values
        # — the real socket sender does this too, and we want to fail
        # fast in tests if a slash command emits an unencodable result.
        encoded = json.dumps(payload, ensure_ascii=False, default=str)
        self.events.append(json.loads(encoded))

    def types(self) -> list[str]:
        return [e.get("type", "?") for e in self.events]

    def by_type(self, t: str) -> list[dict]:
        return [e for e in self.events if e.get("type") == t]

    def first(self, t: str) -> dict | None:
        items = self.by_type(t)
        return items[0] if items else None


class _StubOrch:
    """Stand-in orchestrator: refuses to be called. If the chat-server
    accidentally routes a slash command through the LLM path instead of
    the dispatcher, this raises and the test fails loudly."""

    def chat(self, *a, **k):  # noqa: D401
        raise AssertionError(
            "slash command leaked through to the orchestrator; the server "
            "should have dispatched it deterministically"
        )

    def reset(self):
        return None


def _server(unity_bridge: Any = None) -> ChatServer:
    cfg = Config(api_key="test-key")
    return ChatServer(cfg, port=0, unity_bridge=unity_bridge)


def _user_msg(content: str) -> bytes:
    return json.dumps({"type": "user_message", "content": content}).encode("utf-8")


def _fresh_studio_cwd() -> tuple[StudioState, Path, str]:
    prev_cwd = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="phase67-srv-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    paths.gdd.write_text("# GDD\nA pitch.\n", encoding="utf-8")
    os.chdir(tmp)
    return state, tmp, prev_cwd


# ─────────────────────────────────────── recognition


def test_slash_command_runs_dispatcher_not_orchestrator() -> None:
    """A `/ship` user_message must NEVER hit the orchestrator. The
    stub raises if it's called — so the assertion is implicit."""
    state, _, prev = _fresh_studio_cwd()
    try:
        srv = _server()
        cap = _Capture()
        srv._handle_line(_user_msg("/ship"), _StubOrch(), cap)
        types = cap.types()
        assert "thinking" in types, f"missing thinking event: {types}"
        assert "tool_call" in types, f"missing tool_call event: {types}"
        assert "tool_result" in types, f"missing tool_result event: {types}"
        assert "assistant_text" in types, f"missing assistant_text event: {types}"
        assert "assistant_done" in types, f"missing assistant_done event: {types}"
    finally:
        os.chdir(prev)
    print("OK /ship over chat-server → dispatcher (orchestrator untouched)")


def test_slash_command_tool_call_event_tagged_via_slash() -> None:
    """The synthetic tool_call payload identifies the dispatch source
    so the editor UI can render it differently from LLM-driven calls."""
    state, _, prev = _fresh_studio_cwd()
    try:
        srv = _server()
        cap = _Capture()
        srv._handle_line(_user_msg("/ship"), _StubOrch(), cap)
        tc = cap.first("tool_call")
        assert tc is not None
        assert tc["input"].get("_via") == "slash_command"
        assert tc["input"].get("_line", "").startswith("ship")
    finally:
        os.chdir(prev)
    print("OK tool_call event marks `_via: slash_command` for editor UI")


def test_slash_command_assistant_done_uses_slash_stop_reason() -> None:
    """The final event's stop_reason distinguishes slash from LLM
    completions, so the editor can hide spinner/animation correctly."""
    state, _, prev = _fresh_studio_cwd()
    try:
        srv = _server()
        cap = _Capture()
        srv._handle_line(_user_msg("/ship"), _StubOrch(), cap)
        done = cap.first("assistant_done")
        assert done is not None
        assert done["stop_reason"] == "slash_command", (
            f"expected slash_command stop_reason, got {done['stop_reason']}"
        )
    finally:
        os.chdir(prev)
    print("OK assistant_done.stop_reason='slash_command' on success")


# ─────────────────────────────────────── unknown / empty


def test_unknown_slash_returns_error_event_no_llm() -> None:
    srv = _server()
    cap = _Capture()
    # Stub orch refuses calls — so this WOULD raise if the server tried
    # to send to the LLM. The 'thinking' event happens before dispatch.
    srv._handle_line(_user_msg("/totally_not_a_command"), _StubOrch(), cap)
    err = cap.first("error")
    assert err is not None
    assert "Unknown command" in err["message"]
    assert "/totally_not_a_command" in err["message"]
    done = cap.first("assistant_done")
    assert done is not None
    assert done["stop_reason"] == "unknown_command"
    print("OK unknown slash → error event + assistant_done(unknown_command)")


def test_empty_slash_returns_error_event() -> None:
    srv = _server()
    cap = _Capture()
    srv._handle_line(_user_msg("/"), _StubOrch(), cap)
    err = cap.first("error")
    assert err is not None
    assert "Empty" in err["message"]
    print("OK bare '/' → error event")


# ─────────────────────────────────────── non-slash still flows to LLM


def test_non_slash_message_goes_through_orchestrator() -> None:
    """Free-text user messages must still reach the orchestrator —
    the dispatcher only intercepts inputs that start with '/'."""
    srv = _server()
    cap = _Capture()

    called = {"flag": False}

    class _CountingOrch:
        def chat(self, content, on_tool_call=None, on_tool_result=None, max_iterations=10):
            called["flag"] = True
            from unitytools.core.orchestrator import OrchestratorResult
            return OrchestratorResult(
                text="hi back", tool_calls=[], stop_reason="end_turn"
            )

        def reset(self):
            return None

    srv._handle_line(_user_msg("hello there, no slash"), _CountingOrch(), cap)
    assert called["flag"] is True, (
        "non-slash message should still hit the orchestrator"
    )
    print("OK non-slash messages flow through orchestrator unchanged")


# ─────────────────────────────────────── tool result payload roundtrip


def test_slash_tool_result_contains_ship_payload() -> None:
    """The dispatcher returns the tool's full dict in tool_result['result']
    so the editor can render the ship-readiness numbers, not just a
    summary string."""
    state, _, prev = _fresh_studio_cwd()
    try:
        srv = _server()
        cap = _Capture()
        srv._handle_line(_user_msg("/ship"), _StubOrch(), cap)
        tr = cap.first("tool_result")
        assert tr is not None
        assert tr["tool"] == "studio_ship_readiness_check"
        assert isinstance(tr["result"], dict)
        # ship_readiness_check returns these keys regardless of pass/fail:
        assert "passed" in tr["result"] or "ok" in tr["result"]
    finally:
        os.chdir(prev)
    print("OK /ship tool_result carries the full payload dict")


# ─────────────────────────────────────── Türkçe alias parity


def test_turkish_slash_alias_via_server() -> None:
    """`/yardım` and similar must work via the server too — the
    dispatcher already handles aliasing internally."""
    state, _, prev = _fresh_studio_cwd()
    try:
        # /yapı (build) on a studio with no bridge → expected to surface
        # the "bridge unavailable" message but still emit a clean
        # tool_result + assistant_done. We're checking parity, not success.
        srv = _server(unity_bridge=None)
        cap = _Capture()
        srv._handle_line(_user_msg("/yapı"), _StubOrch(), cap)
        # /yapı with no target → usage error, but DISPATCHED (not unknown)
        assert cap.first("assistant_done") is not None
        # specifically NOT an unknown_command stop_reason — the alias resolved
        done = cap.first("assistant_done")
        assert done["stop_reason"] != "unknown_command", (
            f"Türkçe alias /yapı should resolve to /build, not be unknown; "
            f"got stop_reason={done['stop_reason']}"
        )
    finally:
        os.chdir(prev)
    print("OK /yapı (Türkçe alias for /build) resolves through the server")


def test_turkish_slash_help_alias_via_server() -> None:
    """Phase 68: /yardım now resolves to /help in the dispatcher, so
    the chat-server returns the command listing rather than 'unknown'."""
    srv = _server()
    cap = _Capture()
    srv._handle_line(_user_msg("/yardım"), _StubOrch(), cap)
    done = cap.first("assistant_done")
    assert done is not None
    # After Phase 68 /yardım resolves successfully (not unknown_command)
    assert done["stop_reason"] == "slash_command", (
        f"after Phase 68 /yardım resolves to /help; got stop_reason={done['stop_reason']}"
    )
    text = cap.first("assistant_text")
    assert text is not None
    assert "/help" in text["content"] or "Meta" in text["content"], (
        "/yardım should return the command listing"
    )
    print("OK /yardım resolves to /help over the server (Phase 68 parity)")


# ─────────────────────────────────────── bridge wiring


def test_unity_bridge_reaches_slash_dispatch_via_ctx() -> None:
    """ChatServer(unity_bridge=...) must thread the bridge into the
    DispatchContext used by slash commands, so /build can find Unity."""
    captured_ctx = {}

    fake_bridge = object()

    def _fake_dispatch(line, ctx=None):
        captured_ctx["bridge"] = ctx.unity_bridge if ctx else None
        captured_ctx["line"] = line
        from unitytools.cli.chat_commands import CommandResult
        return CommandResult(handled=True, ok=True, message="ok",
                              tool_name="fake_tool", tool_result={"ok": True})

    import unitytools.cli.chat_commands as cc
    original = cc.dispatch
    cc.dispatch = _fake_dispatch
    try:
        srv = _server(unity_bridge=fake_bridge)
        cap = _Capture()
        srv._handle_line(_user_msg("/build windows"), _StubOrch(), cap)
        assert captured_ctx.get("bridge") is fake_bridge, (
            "the unity bridge passed to ChatServer must reach DispatchContext"
        )
        assert captured_ctx.get("line") == "build windows"
    finally:
        cc.dispatch = original
    print("OK ChatServer.unity_bridge propagates to chat_commands.dispatch ctx")


# ─────────────────────────────────────── ping / reset still work


def test_ping_still_pong_after_phase67() -> None:
    """Sanity check: the slash-command branch lives only in
    user_message handling; ping/reset paths are untouched."""
    srv = _server()
    cap = _Capture()
    srv._handle_line(b'{"type":"ping"}', _StubOrch(), cap)
    assert cap.types() == ["pong"]
    print("OK ping → pong unchanged")


def test_reset_still_works_after_phase67() -> None:
    srv = _server()
    cap = _Capture()

    class _ResetCounting:
        def __init__(self):
            self.reset_calls = 0

        def reset(self):
            self.reset_calls += 1

        def chat(self, *a, **k):
            raise AssertionError("not expected")

    orch = _ResetCounting()
    srv._handle_line(b'{"type":"reset"}', orch, cap)
    assert orch.reset_calls == 1
    types = cap.types()
    assert "assistant_text" in types
    assert "assistant_done" in types
    print("OK reset path unchanged")


# ─────────────────────────────────────── run all


def run_test() -> None:
    test_slash_command_runs_dispatcher_not_orchestrator()
    test_slash_command_tool_call_event_tagged_via_slash()
    test_slash_command_assistant_done_uses_slash_stop_reason()
    test_unknown_slash_returns_error_event_no_llm()
    test_empty_slash_returns_error_event()
    test_non_slash_message_goes_through_orchestrator()
    test_slash_tool_result_contains_ship_payload()
    test_turkish_slash_alias_via_server()
    test_turkish_slash_help_alias_via_server()
    test_unity_bridge_reaches_slash_dispatch_via_ctx()
    test_ping_still_pong_after_phase67()
    test_reset_still_works_after_phase67()
    print("All Phase 67 chat-server slash tests passed")


if __name__ == "__main__":
    run_test()
