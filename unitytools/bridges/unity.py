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


def focus_unity_window() -> bool:
    """Bring the Unity Editor window to the foreground (Windows only).

    Root cause of recurring session friction: when the Unity Editor is
    unfocused/backgrounded, Windows + Unity throttle EditorApplication.
    update to a crawl, so the bridge command pump stalls — `ping`
    answers on the listener thread but real main-thread ops (open_scene,
    recompile) time out. Re-focusing the window un-throttles the loop.

    Safe + idempotent. Returns True if a Unity window was activated.
    Call this before a burst of main-thread bridge ops.
    """
    import sys

    if not sys.platform.startswith("win"):
        return False
    try:
        import subprocess

        ps = (
            "$ws = New-Object -ComObject WScript.Shell;"
            "$p = Get-Process Unity -ErrorAction SilentlyContinue |"
            " Where-Object { $_.MainWindowTitle } |"
            " Sort-Object WorkingSet64 -Descending | Select-Object -First 1;"
            "if ($p) { $ws.AppActivate($p.Id) | Out-Null; 'OK ' + $p.Id }"
            " else { 'NO_UNITY' }"
        )
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=20,
        )
        ok = "OK " in (out.stdout or "")
        if ok:
            logger.info("Unity window focused: %s", out.stdout.strip())
        return ok
    except Exception as exc:  # noqa: BLE001
        logger.debug("focus_unity_window failed: %s", exc)
        return False


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
            preferred = int(self.config.unity_bridge_port)
            candidates = [preferred] + [p for p in range(7777, 7801) if p != preferred]
            for port in candidates:
                s: socket.socket | None = None
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(timeout)
                    s.connect((self.config.unity_bridge_host, port))
                    if not self._probe_connected_socket(s, timeout=min(timeout, 1.0)):
                        s.close()
                        continue
                    s.settimeout(None)  # blocking after handshake
                    self._sock = s
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
    def call(self, method: str, params: Optional[dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        """Editor'da bir method çağır, sonucu döndür. Hata varsa exception fırlatır."""
        timeout = float(timeout if timeout is not None else self.config.unity_rpc_timeout)
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
            except socket.timeout as e:
                # CRITICAL: a timed-out request's response may still
                # arrive later and sit in the socket buffer. If we keep
                # the socket, the NEXT call reads that stale line as its
                # own response -> every subsequent RPC is desynced by one
                # (the cause of "scatter" returning an import_asset dict
                # and screenshots returning a set_scene_view dict). Drop
                # the socket so the next call reconnects fresh & clean.
                try:
                    if self._sock is not None:
                        self._sock.close()
                except Exception:
                    pass
                self._sock = None
                raise TimeoutError(
                    f"Unity RPC zaman aşımı ({timeout:.1f}s). Unity Editor muhtemelen meşgul (compile/import/playmode)."
                ) from e
            except (BrokenPipeError, ConnectionResetError,
                    ConnectionAbortedError, OSError) as e:
                # WinError 10053 (ConnectionAbortedError) and other OSErrors
                # happen during Unity domain reloads. Reset the socket so the
                # next call reconnects fresh instead of wedging forever on a
                # dead handle.
                try:
                    if self._sock is not None:
                        self._sock.close()
                except Exception:
                    pass
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

    @staticmethod
    def _probe_connected_socket(sock: socket.socket, timeout: float) -> bool:
        request = {"id": str(uuid.uuid4())[:8], "method": "ping", "params": {}}
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
