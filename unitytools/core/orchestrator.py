"""LLM orchestrator with Anthropic and Ollama tool-calling backends."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from anthropic import Anthropic

from .config import Config
from .tool_registry import get_tool, to_anthropic_format, to_openai_tool_format

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Sen Unity 6000.x ve Blender ile calisan bir asset pipeline asistanisin.

Kullanici dogal dil ile istek yapar (Turkce veya Ingilizce). Sen bu istegi,
sana verilen tool'lari kullanarak adim adim gerceklestirirsin.

Kurallar:
1. Once plani kisa cumlelerle acikla, sonra tool'lari cagir.
2. Bir tool hata donerse, hatayi kullaniciya acikla, alternatif oner.
3. Dosya yollari her zaman proje root'una gore relative olsun.
4. Asset isimlerinde Turkce karakter kullanma, Ingilizce isim oner.
5. Is bittiginde kisa bir ozet ver.

Mevcut tool'lari gerektiginde baglamadan kullan. Eger bir islem icin tool yoksa,
kullaniciya bunu soyle ve bir workaround oner."""


@dataclass
class ChatMessage:
    role: str
    content: Any


@dataclass
class OrchestratorResult:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ""


class Orchestrator:
    """Runs the provider-specific tool-calling loop."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.client = Anthropic(api_key=config.api_key) if config.provider == "anthropic" else None
        self.history: list[ChatMessage] = []
        self.ollama_messages: list[dict[str, Any]] = []

    def reset(self) -> None:
        self.history = []
        self.ollama_messages = []

    def chat(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
        max_iterations: int = 10,
    ) -> OrchestratorResult:
        if self.config.provider == "ollama":
            return self._chat_ollama(user_message, on_tool_call, on_tool_result, max_iterations)
        return self._chat_anthropic(user_message, on_tool_call, on_tool_result, max_iterations)

    def _chat_anthropic(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]],
        on_tool_result: Optional[Callable[[str, Any], None]],
        max_iterations: int,
    ) -> OrchestratorResult:
        if self.client is None:
            raise RuntimeError("Anthropic client is not initialized")

        self.history.append(ChatMessage(role="user", content=user_message))
        tools = to_anthropic_format()
        final_text = ""
        tool_calls_log: list[dict[str, Any]] = []

        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=self._build_anthropic_messages(),
            )
            self.history.append(ChatMessage(role="assistant", content=response.content))

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            text_blocks = [b for b in response.content if b.type == "text"]
            for tb in text_blocks:
                final_text += tb.text + "\n"

            if response.stop_reason != "tool_use":
                return OrchestratorResult(
                    text=final_text.strip(),
                    tool_calls=tool_calls_log,
                    stop_reason=response.stop_reason,
                )

            tool_results = []
            for block in tool_use_blocks:
                tool_name = block.name
                tool_input = block.input or {}
                if on_tool_call:
                    on_tool_call(tool_name, tool_input)
                try:
                    result = self._execute_tool(tool_name, tool_input)
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(result)})
                    tool_calls_log.append({"name": tool_name, "input": tool_input, "result": result, "ok": True})
                    if on_tool_result:
                        on_tool_result(tool_name, result)
                except Exception as exc:
                    logger.exception("Tool error: %s", tool_name)
                    err = f"Tool calisirken hata: {exc}"
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": err, "is_error": True})
                    tool_calls_log.append({"name": tool_name, "input": tool_input, "error": str(exc), "ok": False})
                    if on_tool_result:
                        on_tool_result(tool_name, {"ok": False, "error": str(exc)})

            self.history.append(ChatMessage(role="user", content=tool_results))

        return OrchestratorResult(
            text=final_text + "\n[Warning: max iterations reached]",
            tool_calls=tool_calls_log,
            stop_reason="max_iterations",
        )

    def _chat_ollama(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]],
        on_tool_result: Optional[Callable[[str, Any], None]],
        max_iterations: int,
    ) -> OrchestratorResult:
        if not self.ollama_messages:
            self.ollama_messages.append({"role": "system", "content": SYSTEM_PROMPT})
        self.ollama_messages.append({"role": "user", "content": user_message})

        final_text = ""
        tool_calls_log: list[dict[str, Any]] = []

        for _ in range(max_iterations):
            response = self._ollama_chat(self.ollama_messages, tools=to_openai_tool_format())
            message = response.get("message") or {}
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            assistant_message: dict[str, Any] = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            self.ollama_messages.append(assistant_message)

            if content:
                final_text += content + "\n"

            if not tool_calls:
                return OrchestratorResult(text=final_text.strip(), tool_calls=tool_calls_log, stop_reason="stop")

            for call in tool_calls:
                function = call.get("function") or {}
                tool_name = function.get("name") or call.get("name")
                tool_input = function.get("arguments") or call.get("arguments") or {}
                if isinstance(tool_input, str):
                    try:
                        tool_input = json.loads(tool_input) if tool_input.strip() else {}
                    except json.JSONDecodeError:
                        tool_input = {}
                if not isinstance(tool_input, dict):
                    tool_input = {}

                if on_tool_call:
                    on_tool_call(tool_name, tool_input)

                try:
                    result = self._execute_tool(tool_name, tool_input)
                    ok = not (isinstance(result, dict) and result.get("ok") is False)
                    tool_calls_log.append({"name": tool_name, "input": tool_input, "result": result, "ok": ok})
                    if on_tool_result:
                        on_tool_result(tool_name, result)
                except Exception as exc:
                    logger.exception("Tool error: %s", tool_name)
                    result = {"ok": False, "error": str(exc)}
                    tool_calls_log.append({"name": tool_name, "input": tool_input, "error": str(exc), "ok": False})
                    if on_tool_result:
                        on_tool_result(tool_name, result)

                self.ollama_messages.append(
                    {
                        "role": "tool",
                        "content": json.dumps(result, ensure_ascii=False),
                        "name": tool_name,
                    }
                )

        return OrchestratorResult(
            text=final_text + "\n[Warning: max iterations reached]",
            tool_calls=tool_calls_log,
            stop_reason="max_iterations",
        )

    def _ollama_chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        host = self.config.ollama_host.rstrip("/")
        payload = {
            "model": self.config.ollama_model,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            f"{host}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama'a baglanilamadi: {exc}. Ollama kurulu ve calisir durumda mi? "
                f"Beklenen adres: {host}"
            ) from exc

    def _execute_tool(self, name: str, params: dict[str, Any]) -> Any:
        spec = get_tool(name)
        if spec is None:
            raise ValueError(f"Bilinmeyen tool: {name}")
        return spec.fn(**params)

    def _build_anthropic_messages(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for msg in self.history:
            content = msg.content
            if msg.role == "assistant" and not isinstance(content, str):
                content = [self._block_to_dict(b) for b in content]
            out.append({"role": msg.role, "content": content})
        return out

    @staticmethod
    def _block_to_dict(block: Any) -> dict[str, Any]:
        if hasattr(block, "model_dump"):
            return block.model_dump()
        if hasattr(block, "dict"):
            return block.dict()
        if block.type == "text":
            return {"type": "text", "text": block.text}
        if block.type == "tool_use":
            return {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
        return {"type": block.type}
