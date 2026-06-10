# -*- coding: utf-8 -*-
"""Test chat server with dual-agent mode."""
import json
import socket
import sys
import time
from threading import Thread


def test_server():
    print("=== CHAT SERVER TEST ===")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 7779))
        sock.close()
    except OSError as exc:
        raise AssertionError("Port 7779 is in use") from exc

    from unitytools.core.chat_server import ChatServer
    from unitytools.core.config import Config

    config = Config.load()
    server = ChatServer(
        config,
        host="127.0.0.1",
        port=7779,
        use_dual_agent=True,
        master_model="qwen2.5:14b-instruct",
        worker_model="qwen2.5:7b-instruct",
    )

    server_thread = Thread(target=server.start_blocking, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.settimeout(5)
    try:
        client.connect(("127.0.0.1", 7779))
        data = client.recv(4096)
        hello = json.loads(data.decode("utf-8").strip().split("\n")[0])
        assert hello.get("type") == "hello"
        assert str(hello.get("mode", "")).startswith("dual-agent")
        assert hello.get("master_model")

        client.send((json.dumps({"type": "ping"}) + "\n").encode("utf-8"))
        data = client.recv(4096)
        pong = json.loads(data.decode("utf-8").strip())
        assert pong.get("type") == "pong"
    finally:
        client.close()
        server.stop()


if __name__ == "__main__":
    test_server()
    sys.exit(0)
