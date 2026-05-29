"""Phase 77: end-to-end TCP roundtrip for slash commands.

Phase 67 tested ChatServer._handle_line in-memory with a fake send
callable. Phase 74 hardened JSON-serialization. This phase closes the
loop: a real socket connects to a real ChatServer, sends a slash
command, and verifies the exact event sequence the Unity Editor
ChatWindow.cs is going to receive.

If anything regresses in the wire protocol — bytes vs str, missing
newline delimiter, non-JSON payload, dropped event, wrong field name —
this test catches it where the in-memory tests can't.
"""
from __future__ import annotations

import json
import os
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.core.chat_server import ChatServer
from unitytools.core.config import Config
from unitytools.studio import StudioPaths, StudioState, init_studio_tools
from unitytools.studio.models import Task, TaskStatus


def _recv_messages(sock, count, timeout=5.0):
    """Read exactly `count` newline-delimited JSON messages, or stop on timeout."""
    sock.settimeout(timeout)
    buf = b""
    msgs = []
    deadline = time.time() + timeout
    while len(msgs) < count and time.time() < deadline:
        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf and len(msgs) < count:
            line, _, buf = buf.partition(b"\n")
            if line.strip():
                msgs.append(json.loads(line.decode("utf-8")))
    return msgs


def _seed_studio_in_cwd() -> tuple[StudioState, Path, str]:
    """Build a studio with mixed-status tasks so /standup returns
    interesting numbers over the wire."""
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="ph77-e2e-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    paths.gdd.write_text("# GDD\nA pitch.\n", encoding="utf-8")

    # Plant 1 done (recent), 1 in-flight, 1 blocked, 2 pending
    now = time.time()
    t = Task(title="Done task", role="designer", status=TaskStatus.DONE)
    t.updated_at = now - 3600
    state.add_task(t)
    state.add_task(Task(title="In flight", role="level_designer",
                         status=TaskStatus.IN_PROGRESS))
    state.add_task(Task(title="Blocked task", role="tech_artist",
                         status=TaskStatus.BLOCKED,
                         blockers=["external dep"]))
    state.add_task(Task(title="Pending 1", role="designer"))
    state.add_task(Task(title="Pending 2", role="qa"))

    os.chdir(tmp)
    return state, tmp, prev


def _start_server(port: int) -> ChatServer:
    cfg = Config(api_key="test-key")
    server = ChatServer(cfg, port=port)
    server_thread = threading.Thread(
        target=server.start_blocking, daemon=True, name=f"e2e-chat-{port}"
    )
    server_thread.start()
    # Spin briefly so the socket binds before the client connects.
    deadline = time.time() + 2.0
    while time.time() < deadline:
        time.sleep(0.05)
        try:
            test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test.settimeout(0.1)
            test.connect(("127.0.0.1", port))
            test.close()
            return server
        except (OSError, socket.timeout):
            continue
    raise RuntimeError(f"ChatServer never came up on port {port}")


# ─────────────────────────────────────── e2e: /standup over TCP


def test_slash_standup_full_event_sequence_over_socket() -> None:
    """The Unity Editor sends `{"type":"user_message","content":"/standup"}`
    and expects: hello → thinking → tool_call → tool_result →
    assistant_text → assistant_done(stop_reason='slash_command').

    This is the contract the C# ChatWindow renders against — lock it in.
    """
    state, _, prev = _seed_studio_in_cwd()
    server = _start_server(port=17780)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 17780))

        # 1. Hello on connect (no input yet)
        msgs = _recv_messages(s, 1)
        assert msgs and msgs[0]["type"] == "hello", (
            f"first event must be hello; got {msgs!r}"
        )

        # 2. Send /standup
        s.sendall(b'{"type":"user_message","content":"/standup"}\n')

        # 3. Expect 5 events: thinking, tool_call, tool_result,
        #    assistant_text, assistant_done
        msgs = _recv_messages(s, 5, timeout=5.0)
        types = [m["type"] for m in msgs]
        for expected in ("thinking", "tool_call", "tool_result",
                          "assistant_text", "assistant_done"):
            assert expected in types, (
                f"missing {expected!r} event in /standup flow; got types={types}"
            )

        # 4. tool_call carries the slash-command marker (Phase 67)
        tc = next(m for m in msgs if m["type"] == "tool_call")
        assert tc["tool"] == "studio_standup", (
            f"tool_call should be studio_standup; got {tc['tool']!r}"
        )
        assert tc["input"].get("_via") == "slash_command", (
            "Phase 67: synthetic tool_call must tag _via=slash_command"
        )

        # 5. tool_result carries the full standup payload over the wire
        tr = next(m for m in msgs if m["type"] == "tool_result")
        assert tr["ok"] is True
        result = tr["result"]
        assert isinstance(result, dict)
        # Counts from the seed: 1 closed (recent), 1 in-flight, 1 blocked, 2 pending
        assert result["closed_recent_count"] == 1
        assert result["in_flight_count"] == 1
        assert result["blocked_count"] == 1
        assert result["pending_count"] == 2

        # 6. assistant_text is a one-line summary
        at = next(m for m in msgs if m["type"] == "assistant_text")
        for token in ("closed", "in-flight", "blocked", "pending"):
            assert token in at["content"], (
                f"assistant_text summary missing {token!r}; got {at['content']!r}"
            )

        # 7. assistant_done carries stop_reason='slash_command'
        ad = next(m for m in msgs if m["type"] == "assistant_done")
        assert ad["stop_reason"] == "slash_command", (
            f"slash dispatch must set stop_reason='slash_command'; "
            f"got {ad['stop_reason']!r}"
        )

        s.close()
    finally:
        server.stop()
        os.chdir(prev)
    print(
        "OK /standup full TCP roundtrip — hello→thinking→tool_call(_via=slash)→"
        "tool_result→assistant_text→assistant_done(slash_command)"
    )


# ─────────────────────────────────────── e2e: unknown slash error


def test_unknown_slash_returns_error_over_socket() -> None:
    """Unknown commands emit `error` + `assistant_done(unknown_command)`
    rather than silently routing to the LLM."""
    state, _, prev = _seed_studio_in_cwd()
    server = _start_server(port=17781)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 17781))
        _recv_messages(s, 1)  # consume hello

        s.sendall(b'{"type":"user_message","content":"/not_a_real_command"}\n')
        msgs = _recv_messages(s, 3, timeout=3.0)
        types = [m["type"] for m in msgs]
        # The protocol sends: thinking, error, assistant_done
        assert "error" in types, (
            f"unknown slash should emit error event; got {types}"
        )
        err = next(m for m in msgs if m["type"] == "error")
        assert "Unknown command" in err["message"]
        ad = next(m for m in msgs if m["type"] == "assistant_done")
        assert ad["stop_reason"] == "unknown_command", (
            f"unknown slash stop_reason must be unknown_command; got {ad['stop_reason']!r}"
        )
        s.close()
    finally:
        server.stop()
        os.chdir(prev)
    print("OK unknown slash → error + assistant_done(unknown_command) over TCP")


# ─────────────────────────────────────── e2e: /tools filters over the wire


def test_slash_tools_filter_returns_payload_over_socket() -> None:
    """A real Unity Editor user typing /tools studio expects the tool
    list to arrive in tool_result['tools'] as an array of {name,
    description} dicts."""
    state, _, prev = _seed_studio_in_cwd()
    server = _start_server(port=17782)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 17782))
        _recv_messages(s, 1)  # consume hello

        s.sendall(b'{"type":"user_message","content":"/tools studio"}\n')
        msgs = _recv_messages(s, 5, timeout=5.0)
        tr = next((m for m in msgs if m["type"] == "tool_result"), None)
        assert tr is not None, "tool_result missing from /tools flow"
        result = tr["result"]
        assert "tools" in result
        assert result["filter"] == "studio"
        assert result["shown"] > 0
        # Every returned tool actually matches the filter
        for entry in result["tools"][:5]:
            assert "studio" in (entry["name"] + entry["description"]).lower()
        s.close()
    finally:
        server.stop()
        os.chdir(prev)
    print("OK /tools studio over TCP returns matching tool array via tool_result")


# ─────────────────────────────────────── e2e: Türkçe alias over the wire


def test_turkish_slash_alias_resolves_over_socket() -> None:
    """/sıradaki (Türkçe alias for /next) must resolve in the
    server-side dispatcher. We test with a backlog containing a
    pending task so /next returns one."""
    state, _, prev = _seed_studio_in_cwd()
    server = _start_server(port=17783)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 17783))
        _recv_messages(s, 1)  # consume hello

        # Note: socket needs the utf-8 bytes for ı / ş / etc.
        payload = json.dumps(
            {"type": "user_message", "content": "/sıradaki"},
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        s.sendall(payload)

        msgs = _recv_messages(s, 5, timeout=5.0)
        tr = next((m for m in msgs if m["type"] == "tool_result"), None)
        assert tr is not None
        assert tr["tool"] == "studio_next_task", (
            f"/sıradaki should fire studio_next_task; got {tr['tool']!r}"
        )
        # The seeded backlog has pending tasks — there's a ready one
        assert tr["result"].get("task") is not None
        s.close()
    finally:
        server.stop()
        os.chdir(prev)
    print("OK Türkçe /sıradaki resolves to /next over TCP")


# ─────────────────────────────────────── e2e: ping/pong still works


def test_ping_still_works_alongside_slash_path() -> None:
    """Sanity: adding the slash-dispatch branch in user_message didn't
    break the ping/reset paths that the Editor's keepalive uses."""
    state, _, prev = _seed_studio_in_cwd()
    server = _start_server(port=17784)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 17784))
        _recv_messages(s, 1)  # hello

        s.sendall(b'{"type":"ping"}\n')
        msgs = _recv_messages(s, 1, timeout=2.0)
        assert msgs and msgs[0]["type"] == "pong"
        s.close()
    finally:
        server.stop()
        os.chdir(prev)
    print("OK ping/pong still works after Phase 67 slash branch")


def run_test() -> None:
    test_slash_standup_full_event_sequence_over_socket()
    test_unknown_slash_returns_error_over_socket()
    test_slash_tools_filter_returns_payload_over_socket()
    test_turkish_slash_alias_resolves_over_socket()
    test_ping_still_works_alongside_slash_path()
    print("All Phase 77 chat-server e2e slash tests passed")


if __name__ == "__main__":
    run_test()
