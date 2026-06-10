"""Unreal Editor TCP bridge client."""
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from ..core.config import Config
from ..core.protocol import RpcRequest, RpcResponse
from ..core.security import is_loopback_host

logger = logging.getLogger(__name__)


class UnrealNotConnectedError(RuntimeError):
    pass


class UnrealBridge:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._sock: Optional[socket.socket] = None
        self._lock = threading.Lock()
        self._buffer = b""

    def connect(self, timeout: float = 2.0) -> bool:
        with self._lock:
            if self._sock is not None:
                return True
            preferred = int(getattr(self.config, "unreal_bridge_port", 8777))
            host = getattr(self.config, "unreal_bridge_host", "127.0.0.1")
            if not is_loopback_host(host) and not getattr(self.config, "allow_remote", False):
                logger.error(
                    "Unreal bridge host %s loopback degil; loopback disi baglanti icin "
                    "UNITYTOOLS_ALLOW_REMOTE=1 ve bir token gerekir.",
                    host,
                )
                return False
            token = getattr(self.config, "bridge_token", "") or ""
            active_project = os.getenv("UNREALTOOLS_ACTIVE_PROJECT", "").strip()
            candidates = [preferred] + [p for p in range(8777, 8801) if p != preferred]
            for port in candidates:
                s: socket.socket | None = None
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    connect_timeout = timeout if port == preferred else min(timeout, 0.15)
                    s.settimeout(connect_timeout)
                    s.connect((host, port))
                    if not self._probe_connected_socket(s, timeout=min(connect_timeout, 1.0), token=token):
                        s.close()
                        continue
                    if active_project and not self._probe_project_match(s, active_project, timeout=min(timeout, 1.0), token=token):
                        s.close()
                        continue
                    s.settimeout(None)
                    self._sock = s
                    self.config.unreal_bridge_port = port
                    logger.info("Unreal bridge connected: %s:%d", host, port)
                    return True
                except (ConnectionRefusedError, socket.timeout, OSError) as e:
                    logger.debug("Unreal bridge connection failed (%d): %s", port, e)
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

    def call(self, method: str, params: Optional[dict[str, Any]] = None, timeout: Optional[float] = None) -> Any:
        timeout = float(timeout if timeout is not None else getattr(self.config, "unreal_rpc_timeout", 180.0))
        if not self.is_connected():
            raise UnrealNotConnectedError("Could not connect to Unreal Editor bridge. Is Unreal open and UnrealToolsBridge enabled?")
        request = RpcRequest(
            id=str(uuid.uuid4())[:8],
            method=method,
            params=params or {},
            token=(getattr(self.config, "bridge_token", "") or None),
        )
        response = self._send_and_receive(request, timeout=timeout)
        if response.error:
            raise RuntimeError(f"Unreal RPC error ({response.error.code}): {response.error.message}")
        return response.result

    def _send_and_receive(self, request: RpcRequest, timeout: float) -> RpcResponse:
        with self._lock:
            assert self._sock is not None
            payload = request.model_dump_json(exclude_none=True).encode("utf-8") + b"\n"
            try:
                self._sock.sendall(payload)
                self._sock.settimeout(timeout)
                line = self._read_line()
            except socket.timeout as e:
                raise TimeoutError(f"Unreal RPC timeout ({timeout:.1f}s). Editor may be busy compiling/importing.") from e
            except (BrokenPipeError, ConnectionResetError) as e:
                self._sock = None
                raise UnrealNotConnectedError(f"Connection lost: {e}") from e
            finally:
                if self._sock is not None:
                    self._sock.settimeout(None)
        data = json.loads(line.decode("utf-8"))
        return RpcResponse.model_validate(data)

    def _read_line(self) -> bytes:
        assert self._sock is not None
        while b"\n" not in self._buffer:
            chunk = self._sock.recv(65536)
            if not chunk:
                raise ConnectionResetError("Unreal closed connection")
            self._buffer += chunk
        line, _, rest = self._buffer.partition(b"\n")
        self._buffer = rest
        return line

    def ping(self) -> bool:
        try:
            result = self.call("ping", timeout=2.0)
            return bool(result and result.get("pong"))
        except Exception:
            return False

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
                chunk = sock.recv(65536)
                if not chunk:
                    return False
                buffer += chunk
            line, _, _ = buffer.partition(b"\n")
            data = json.loads(line.decode("utf-8"))
            result = data.get("result") or {}
            return bool(result.get("pong"))
        except Exception:
            return False

    @staticmethod
    def _probe_project_match(sock: socket.socket, active_project: str, timeout: float, token: str = "") -> bool:
        request = {"id": str(uuid.uuid4())[:8], "method": "get_project_info", "params": {}}
        if token:
            request["token"] = token
        try:
            sock.settimeout(timeout)
            sock.sendall(json.dumps(request).encode("utf-8") + b"\n")
            buffer = b""
            while b"\n" not in buffer:
                chunk = sock.recv(65536)
                if not chunk:
                    return False
                buffer += chunk
            line, _, _ = buffer.partition(b"\n")
            data = json.loads(line.decode("utf-8"))
            info = data.get("result") or {}
            remote = str(info.get("project_dir_abs") or info.get("project_dir") or "")
            if not remote:
                return False
            active_norm = _norm_path(active_project)
            remote_norm = _norm_path(remote)
            return bool(active_norm and remote_norm and active_norm == remote_norm)
        except Exception:
            return False


def _norm_path(value: str) -> str:
    try:
        return str(Path(value).expanduser().resolve()).rstrip("\\/").lower()
    except Exception:
        return value.replace("/", "\\").rstrip("\\").lower()
