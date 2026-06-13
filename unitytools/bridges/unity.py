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
import time
import uuid
from typing import Any, Optional

from ..core.config import Config
from ..core.protocol import RpcRequest, RpcResponse
from ..core.security import is_loopback_host

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
        """Editor listener'a bağlanmayı dene.

        Windows sometimes leaves a stale localhost listener after Unity reloads.
        A plain TCP connect can succeed while the old bridge never answers, so
        every candidate port must return a real ping before we accept it.
        """
        with self._lock:
            if self._sock is not None:
                return True
            host = self.config.unity_bridge_host
            if not is_loopback_host(host) and not getattr(self.config, "allow_remote", False):
                logger.error(
                    "Unity bridge host %s loopback degil; loopback disi baglanti icin "
                    "UNITYTOOLS_ALLOW_REMOTE=1 ve bir token gerekir.",
                    host,
                )
                return False
            token = getattr(self.config, "bridge_token", "") or ""
            preferred = int(self.config.unity_bridge_port)
            candidates = [preferred] + [p for p in range(7777, 7801) if p != preferred]
            for port in candidates:
                s: socket.socket | None = None
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    s.connect((host, port))
                    if not self._probe_connected_socket(s, timeout=min(timeout, 1.0), token=token):
                        s.close()
                        continue
                    s.settimeout(None)  # blocking after handshake
                    self._sock = s
                    self._buffer = b""  # eski bağlantıdan yarım satır taşmasın
                    self.config.unity_bridge_port = port
                    logger.info(
                        "Unity bridge bağlandı: %s:%d",
                        self.config.unity_bridge_host,
                        port,
                    )
                    return True
                except (ConnectionRefusedError, socket.timeout, OSError) as e:
                    logger.debug("Unity bridge bağlantı hatası (%d): %s", port, e)
                    if s is not None:
                        try:
                            s.close()
                        except Exception:
                            pass
                    self._sock = None
            return False
    def disconnect(self) -> None:
        with self._lock:
            self._drop_connection_locked()
    def _drop_connection_locked(self) -> None:
        """Soketi kapat ve buffer'ı sıfırla. self._lock tutulurken çağrılmalı."""
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
        self._buffer = b""
    def is_connected(self) -> bool:
        if self._sock is not None:
            return True
        return self.connect()
    # ---------- RPC ----------
    def call(self, method: str, params: Optional[dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        """Editor'da bir method çağır, sonucu döndür. Hata varsa exception fırlatır."""
        timeout = float(timeout if timeout is not None else self.config.unity_rpc_timeout)
        if not self.is_connected():
            raise UnityNotConnectedError(
                "Unity Editor'a bağlanılamadı. Editor'ün açık olduğundan ve "
                "BridgeServer'ın çalıştığından emin ol."
            )
        request = RpcRequest(
            id=str(uuid.uuid4())[:8],
            method=method,
            params=params or {},
            token=(getattr(self.config, "bridge_token", "") or None),
        )
        response = self._send_and_receive(request, timeout=timeout)
        if response.error:
            raise RuntimeError(f"Unity RPC hatası ({response.error.code}): {response.error.message}")
        return response.result
    def _send_and_receive(self, request: RpcRequest, timeout: float) -> RpcResponse:
        with self._lock:
            assert self._sock is not None
            payload = request.model_dump_json(exclude_none=True).encode("utf-8") + b"\n"
            deadline = time.monotonic() + timeout
            try:
                self._sock.sendall(payload)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise socket.timeout()
                    self._sock.settimeout(remaining)
                    line = self._read_line()
                    try:
                        data = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as e:
                        self._drop_connection_locked()
                        raise UnityNotConnectedError(
                            f"Bozuk RPC yanıtı alındı, bağlantı sıfırlandı: {e}"
                        ) from e
                    if data.get("id") == request.id:
                        return RpcResponse.model_validate(data)
                    # Zaman aşımına uğramış önceki bir çağrının geç gelen yanıtı;
                    # yeni isteğin sonucu sanılmasın diye atılıyor.
                    logger.warning(
                        "Eşleşmeyen RPC yanıtı atıldı (gelen id=%s, beklenen=%s, method=%s)",
                        data.get("id"), request.id, request.method,
                    )
            except socket.timeout as e:
                raise TimeoutError(
                    f"Unity RPC zaman aşımı ({timeout:.1f}s). Unity Editor muhtemelen meşgul (compile/import/playmode)."
                ) from e
            except (BrokenPipeError, ConnectionResetError) as e:
                self._drop_connection_locked()
                raise UnityNotConnectedError(f"Bağlantı koptu: {e}") from e
            finally:
                if self._sock is not None:
                    self._sock.settimeout(None)
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

    @staticmethod
    def _probe_connected_socket(sock: socket.socket, timeout: float, token: str = "") -> bool:
        request = {"id": str(uuid.uuid4())[:8], "method": "ping", "params": {}}
        if token:
            request["token"] = token
        try:
            sock.settimeout(timeout)
            sock.sendall(json.dumps(request).encode("utf-8") + b"\n")
            buffer = b""
            while b"\n" not in buffer:
                chunk = sock.recv(4096)
                if not chunk:
                    return False
                buffer += chunk
            line, _, _ = buffer.partition(b"\n")
            data = json.loads(line.decode("utf-8"))
            result = data.get("result") or {}
            return bool(result.get("pong"))
        except Exception:
            return False

    # ---------- yüksek seviye yardımcılar ----------
    def ping(self) -> bool:
        try:
            result = self.call("ping", timeout=2.0)
            return bool(result and result.get("pong"))
        except Exception:
            return False
