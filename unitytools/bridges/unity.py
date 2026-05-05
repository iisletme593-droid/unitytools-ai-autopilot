"""Unity bridge: Editor içinde çalışan TCP listener'a JSON-RPC yollar.

Editor tarafı: `unity_plugin/Editor/Bridge/BridgeServer.cs`
Protokol: her satır bir JSON mesajı, satır sonu \\n.

Kullanım:
    bridge = UnityBridge(config)
    if bridge.is_connected():
        result = bridge.call("create_primitive", {"type": "Cube", "name": "MyCube"})
"""
from __future__ import annotations

import json
import logging
import socket
import threading
import uuid
from typing import Any, Optional

from ..core.config import Config
from ..core.protocol import RpcRequest, RpcResponse

logger = logging.getLogger(__name__)


class UnityNotConnectedError(RuntimeError):
    pass


class UnityBridge:
    """Tek istemcili, senkron TCP client. Editor tarafı listener yapar."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._buffer = b""

    # ---------- bağlantı yönetimi ----------

    def connect(self, timeout: float = 2.0) -> bool:
        """Editor listener'a bağlanmayı dene. True dönerse bağlandı demektir."""
        with self._lock:
            if self._sock is not None:
                return True
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((self.config.unity_bridge_host, self.config.unity_bridge_port))
                s.settimeout(None)  # blocking after handshake
                self._sock = s
                logger.info(
                    "Unity bridge bağlandı: %s:%d",
                    self.config.unity_bridge_host,
                    self.config.unity_bridge_port,
                )
                return True
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                logger.debug("Unity bridge bağlantı hatası: %s", e)
                self._sock = None
                return False

    def disconnect(self) -> None:
        with self._lock:
            if self._sock is not None:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None

    def is_connected(self) -> bool:
        if self._sock is not None:
            return True
        return self.connect()

    # ---------- RPC ----------

    def call(self, method: str, params: Optional[dict[str, Any]] = None, timeout: float = 30.0) -> Any:
        """Editor'da bir method çağır, sonucu döndür. Hata varsa exception fırlatır."""
        if not self.is_connected():
            raise UnityNotConnectedError(
                "Unity Editor'a bağlanılamadı. Editor'ün açık olduğundan ve "
                "BridgeServer'ın çalıştığından emin ol."
            )

        request = RpcRequest(id=str(uuid.uuid4())[:8], method=method, params=params or {})
        response = self._send_and_receive(request, timeout=timeout)

        if response.error:
            raise RuntimeError(f"Unity RPC hatası ({response.error.code}): {response.error.message}")
        return response.result

    def _send_and_receive(self, request: RpcRequest, timeout: float) -> RpcResponse:
        with self._lock:
            assert self._sock is not None
            payload = request.model_dump_json().encode("utf-8") + b"\n"
            try:
                self._sock.sendall(payload)
                self._sock.settimeout(timeout)
                line = self._read_line()
            except (BrokenPipeError, ConnectionResetError, socket.timeout) as e:
                self._sock = None
                raise UnityNotConnectedError(f"Bağlantı koptu: {e}") from e
            finally:
                if self._sock is not None:
                    self._sock.settimeout(None)

        data = json.loads(line.decode("utf-8"))
        return RpcResponse.model_validate(data)

    def _read_line(self) -> bytes:
        """Newline'a kadar oku. Buffer'ı state olarak tut."""
        assert self._sock is not None
        while b"\n" not in self._buffer:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionResetError("Editor bağlantıyı kapattı")
            self._buffer += chunk
        line, _, rest = self._buffer.partition(b"\n")
        self._buffer = rest
        return line

    # ---------- yüksek seviye yardımcılar ----------

    def ping(self) -> bool:
        try:
            result = self.call("ping", timeout=2.0)
            return bool(result and result.get("pong"))
        except Exception:
            return False
