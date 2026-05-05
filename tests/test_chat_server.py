"""End-to-end ChatServer protocol test with a stubbed orchestrator."""
import json
import socket
import threading
import time
from unittest.mock import patch

from unitytools.core.config import Config
from unitytools.core.chat_server import ChatServer
from unitytools.core.orchestrator import OrchestratorResult


def fake_orch_chat(self, message, on_tool_call=None, on_tool_result=None, max_iterations=10):
    """Fake orchestrator that simulates one Unity tool call."""
    if on_tool_call:
        on_tool_call("unity_create_primitive", {"type": "Cube", "name": "Test"})
    if on_tool_result:
        on_tool_result("unity_create_primitive", {"ok": True, "name": "Test", "instance_id": 99})
    return OrchestratorResult(
        text=f"Your message was: '{message}'. I created a cube.",
        tool_calls=[],
        stop_reason="end_turn",
    )


def recv_messages(sock, count, timeout=5.0):
    """Read exactly count newline-delimited JSON messages, or until timeout."""
    sock.settimeout(timeout)
    buf = b""
    msgs = []
    deadline = time.time() + timeout
    while len(msgs) < count and time.time() < deadline:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
        while b"\n" in buf and len(msgs) < count:
            line, _, buf = buf.partition(b"\n")
            if line.strip():
                msgs.append(json.loads(line.decode("utf-8")))
    return msgs


def run_test():
    cfg = Config(api_key="test-key")
    server = ChatServer(cfg, port=17778)

    with patch("unitytools.core.orchestrator.Orchestrator.chat", fake_orch_chat):
        server_thread = threading.Thread(target=server.start_blocking, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", 17778))

        s.sendall(b'{"type":"ping"}\n')
        msgs = recv_messages(s, 1)
        assert msgs[0]["type"] == "pong", f"Ping failed: {msgs}"
        print("OK ping/pong")

        s.sendall(b'{"type":"user_message","content":"merhaba"}\n')
        msgs = recv_messages(s, 5, timeout=3)
        types = [m["type"] for m in msgs]
        print(f"Flow: {types}")
        assert "thinking" in types, "missing thinking"
        assert "tool_call" in types, "missing tool_call"
        assert "tool_result" in types, "missing tool_result"
        assert "assistant_text" in types, "missing assistant_text"
        assert "assistant_done" in types, "missing assistant_done"

        tool_call = next(m for m in msgs if m["type"] == "tool_call")
        assert tool_call["tool"] == "unity_create_primitive"
        assert tool_call["input"]["type"] == "Cube"
        print("OK tool_call")

        tool_result = next(m for m in msgs if m["type"] == "tool_result")
        assert tool_result["ok"] is True
        print("OK tool_result")

        assistant = next(m for m in msgs if m["type"] == "assistant_text")
        assert "merhaba" in assistant["content"]
        print("OK assistant_text")

        s.sendall(b'{"type":"reset"}\n')
        msgs = recv_messages(s, 2, timeout=2)
        types = [m["type"] for m in msgs]
        assert "assistant_done" in types
        print("OK reset")

        s.close()
        server.stop()

    print("All tests passed")


if __name__ == "__main__":
    run_test()
