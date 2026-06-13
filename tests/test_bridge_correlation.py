"""Bridge RPC yanıt korelasyonu testleri.

Zaman aşımına uğrayan bir çağrının geç gelen yanıtı, bir sonraki çağrının
sonucu sanılmamalı (id eşleşmesi). Araya giren bayat/yabancı yanıtlar da
atılmalı.
"""
from __future__ import annotations

import json
import socket
import threading

import pytest

from unitytools.bridges.unity import UnityBridge
from unitytools.bridges.unreal import UnrealBridge
from unitytools.core.config import Config


class ScriptedBridgeServer:
    """Satır-tabanlı sahte editor bridge sunucusu (tek istemci).

    - ping: pong döner; bekleyen geç yanıt varsa ÖNCE onu gönderir
      (timeout sonrası geç gelen yanıt senaryosu).
    - slow_op: hiç yanıt vermez, yanıt id'sini sonraya saklar.
    - noisy_op: önce yanlış id'li bir yanıt, sonra doğrusunu gönderir.
    """

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        self.sock.listen(1)
        self.conn: socket.socket | None = None
        self.delayed_id: str | None = None
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        try:
            self.conn, _ = self.sock.accept()
        except OSError:
            return
        buffer = b""
        while True:
            try:
                chunk = self.conn.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, _, buffer = buffer.partition(b"\n")
                if line.strip():
                    self._handle(json.loads(line.decode("utf-8")))

    def _send(self, payload: dict) -> None:
        assert self.conn is not None
        self.conn.sendall(json.dumps(payload).encode("utf-8") + b"\n")

    def _handle(self, req: dict) -> None:
        method = req["method"]
        if method == "ping":
            if self.delayed_id is not None:
                self._send({"id": self.delayed_id, "result": {"slow": True}})
                self.delayed_id = None
            self._send({"id": req["id"], "result": {"pong": True}})
        elif method == "slow_op":
            self.delayed_id = req["id"]
        elif method == "noisy_op":
            self._send({"id": "bogus-stale-id", "result": {"stale": True}})
            self._send({"id": req["id"], "result": {"value": 42}})

    def close(self) -> None:
        for s in (self.conn, self.sock):
            if s is not None:
                try:
                    s.close()
                except OSError:
                    pass


def _make_bridge(kind: str, port: int):
    if kind == "unity":
        cfg = Config(unity_bridge_port=port, unity_rpc_timeout=5.0)
        return UnityBridge(cfg)
    cfg = Config(unreal_bridge_port=port, unreal_rpc_timeout=5.0)
    return UnrealBridge(cfg)


@pytest.fixture()
def server():
    srv = ScriptedBridgeServer()
    yield srv
    srv.close()


@pytest.mark.parametrize("kind", ["unity", "unreal"])
def test_mismatched_response_is_discarded(server, kind):
    bridge = _make_bridge(kind, server.port)
    assert bridge.connect(timeout=2.0)
    result = bridge.call("noisy_op", timeout=5.0)
    assert result == {"value": 42}
    bridge.disconnect()


@pytest.mark.parametrize("kind", ["unity", "unreal"])
def test_late_reply_after_timeout_not_mistaken_for_next_call(server, kind):
    bridge = _make_bridge(kind, server.port)
    assert bridge.connect(timeout=2.0)
    with pytest.raises(TimeoutError):
        bridge.call("slow_op", timeout=0.3)
    # Sunucu, ping isteğini görünce önce slow_op'un geç yanıtını gönderiyor.
    # İstemci onu atıp kendi ping yanıtını beklemeli.
    result = bridge.call("ping", timeout=5.0)
    assert result.get("pong") is True
    bridge.disconnect()
