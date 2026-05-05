"""TCP chat server used by the embedded Unity Editor AI panel.

Unity connects to this process on port 7778, sends newline-delimited JSON
messages, and receives tool-call progress plus final assistant text.

İlk bağlantı kurulduğunda istemciye bir `hello` mesajı gönderilir; böylece
Unity tarafı süreç başarıyla ayağa kalkmış mı yoksa import sırasında ölmüş mü
olduğunu anlayabilir.
"""
from __future__ import annotations

import base64
import json
import logging
import socket
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .config import Config
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)


@dataclass
class ClientHandle:
    sock: socket.socket
    addr: tuple
    alive: bool = True


class ChatServer:
    """Small newline-delimited JSON chat server.

    Each client gets an isolated orchestrator instance so chat history does not
    leak between Unity windows or test clients.
    """

    SERVER_VERSION = "2.0.0"

    def __init__(
        self,
        config: Config,
        host: str = "127.0.0.1",
        port: int = 7778,
    ) -> None:
        self.config = config
        self.host = host
        self.port = port
        self._listen_sock: Optional[socket.socket] = None
        self._running = False
        self._client_threads: list[threading.Thread] = []

    def start_blocking(self) -> None:
        self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self._listen_sock.bind((self.host, self.port))
        except OSError as e:
            logger.error("ChatServer port'u acilamadi %s:%d -> %s", self.host, self.port, e)
            raise
        self._listen_sock.listen(5)
        self._running = True
        logger.info("ChatServer listening: %s:%d", self.host, self.port)

        try:
            while self._running:
                try:
                    conn, addr = self._listen_sock.accept()
                except OSError:
                    break
                logger.info("New chat client: %s", addr)
                t = threading.Thread(
                    target=self._serve_client,
                    args=(ClientHandle(conn, addr),),
                    daemon=True,
                    name=f"chat-{addr[1]}",
                )
                t.start()
                self._client_threads.append(t)
        finally:
            self.stop()

    def stop(self) -> None:
        self._running = False
        if self._listen_sock is not None:
            try:
                self._listen_sock.close()
            except Exception:
                pass
        self._listen_sock = None

    def _serve_client(self, client: ClientHandle) -> None:
        orch = Orchestrator(self.config)
        send = self._make_sender(client)

        # İlk handshake: Unity tarafı süreç sağlığını bundan anlar.
        try:
            tool_count = 0
            try:
                from .tool_registry import get_all_tools

                tool_count = len(get_all_tools())
            except Exception:
                pass
            send(
                {
                    "type": "hello",
                    "version": self.SERVER_VERSION,
                    "provider": self.config.provider,
                    "model": self.config.model if self.config.provider == "anthropic" else self.config.ollama_model,
                    "tools_loaded": tool_count,
                }
            )
        except Exception:
            logger.exception("hello sent failed")

        buffer = b""
        try:
            while client.alive and self._running:
                try:
                    chunk = client.sock.recv(4096)
                except (ConnectionResetError, OSError):
                    break
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, _, buffer = buffer.partition(b"\n")
                    if not line.strip():
                        continue
                    self._handle_line(line, orch, send)
        except Exception as e:
            logger.exception("Client error: %s", client.addr)
            try:
                send({"type": "error", "message": str(e)})
            except Exception:
                pass
        finally:
            try:
                client.sock.close()
            except Exception:
                pass
            logger.info("Chat client closed: %s", client.addr)

    def _handle_line(
        self,
        line: bytes,
        orch: Orchestrator,
        send: Callable[[dict], None],
    ) -> None:
        try:
            msg = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as e:
            send({"type": "error", "message": f"Invalid JSON: {e}"})
            return

        msg_type = msg.get("type")

        if msg_type == "ping":
            send({"type": "pong"})
            return

        if msg_type == "reset":
            orch.reset()
            send({"type": "assistant_text", "content": "History cleared.", "done": True})
            send({"type": "assistant_done", "stop_reason": "reset"})
            return

        if msg_type == "user_message":
            content = (msg.get("content") or "").strip()
            if not content:
                send({"type": "error", "message": "Empty message"})
                return
            self._process_user_message(content, orch, send)
            return

        if msg_type == "user_message_with_images":
            content = (msg.get("content") or "").strip()
            images = msg.get("images") or []
            if not content and not images:
                send({"type": "error", "message": "Empty message"})
                return
            if self.config.provider != "anthropic":
                send(
                    {
                        "type": "error",
                        "message": "Image input requires UNITYTOOLS_PROVIDER=anthropic (Claude vision).",
                    }
                )
                return
            blocks: list[dict[str, Any]] = []
            if content:
                blocks.append({"type": "text", "text": content})
            for img in images:
                try:
                    mime = str(img.get("mime") or "image/png")
                    data_b64 = str(img.get("data_base64") or "")
                    if not data_b64.strip():
                        continue
                    base64.b64decode(data_b64, validate=False)
                    blocks.append(
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": mime, "data": data_b64},
                        }
                    )
                except Exception:
                    continue
            self._process_user_message(blocks, orch, send)
            return

        send({"type": "error", "message": f"Unknown message type: {msg_type}"})

    def _process_user_message(
        self,
        content: Any,
        orch: Orchestrator,
        send: Callable[[dict], None],
    ) -> None:
        send({"type": "thinking"})

        def on_tool_call(name: str, params: dict) -> None:
            send({"type": "tool_call", "tool": name, "input": params})

        def on_tool_result(name: str, result: Any) -> None:
            ok = isinstance(result, dict) and result.get("ok", True)
            error = None
            payload = result
            if isinstance(result, dict) and "error" in result and not ok:
                error = result.get("error")
            send(
                {
                    "type": "tool_result",
                    "tool": name,
                    "ok": ok,
                    "result": payload,
                    "error": error,
                }
            )

        try:
            result = orch.chat(
                content,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
        except Exception as e:
            logger.exception("Orchestrator error")
            send({"type": "error", "message": str(e), "error_type": type(e).__name__})
            return

        if result.text:
            send({"type": "assistant_text", "content": result.text, "done": True})
        send({"type": "assistant_done", "stop_reason": result.stop_reason})

    @staticmethod
    def _make_sender(client: ClientHandle) -> Callable[[dict], None]:
        lock = threading.Lock()

        def send(payload: dict) -> None:
            if not client.alive:
                return
            try:
                data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")
                with lock:
                    client.sock.sendall(data)
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                logger.debug("send failed (%s), marking client dead", e)
                client.alive = False

        return send
