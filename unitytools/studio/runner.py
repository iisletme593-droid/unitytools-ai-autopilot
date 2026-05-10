"""RoleRunner — drive a single role agent through one brief.

This is a narrower tool-calling loop than core/orchestrator.py: it
takes a RoleConfig, hands the LLM only that role's allowed tools and
its dedicated system prompt, runs the loop until the model stops
producing tool calls, and returns the final text plus a tool-call log.

The LLM call is injected via a `LLMClient` protocol so tests can swap a
deterministic fake without monkey-patching anthropic / urllib.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from ..core.config import Config
from ..core.tool_registry import get_tool, to_anthropic_format
from .roles import RoleConfig

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRecord:
    name: str
    input: dict
    result: Any
    ok: bool


@dataclass
class RoleRunResult:
    role_id: str
    text: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    iterations: int = 0
    stop_reason: str = "end_turn"


class LLMClient(Protocol):
    """Single-method interface the runner depends on.

    `tools` is the schema list to advertise. Returns a dict shaped like:
        {
            "text": "free-form assistant text (may be empty)",
            "tool_calls": [
                {"id": "...", "name": "...", "input": {...}},
                ...
            ],
            "stop_reason": "end_turn" | "tool_use" | ...,
        }
    `messages` is the conversation so far in a provider-neutral form
    (role: 'user' | 'assistant' | 'tool', plus matching content).
    """

    def complete(self, system: str, tools: list[dict], messages: list[dict]) -> dict: ...


class AnthropicClient:
    """Minimal Anthropic adapter that satisfies LLMClient."""

    def __init__(self, config: Config):
        from anthropic import Anthropic  # imported lazily so tests don't need network deps

        if not config.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; cannot use Anthropic provider.")
        self._client = Anthropic(api_key=config.api_key)
        self._model = config.model
        self._max_tokens = max(1024, int(getattr(config, "max_tokens", 4096)))

    def complete(self, system: str, tools: list[dict], messages: list[dict]) -> dict:
        # Translate provider-neutral messages back into Anthropic's format.
        anthropic_msgs: list[dict] = []
        for m in messages:
            role = m["role"]
            content = m["content"]
            if role == "tool":
                anthropic_msgs.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m["tool_use_id"],
                                "content": content,
                            }
                        ],
                    }
                )
                continue
            anthropic_msgs.append({"role": role, "content": content})

        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            tools=tools,
            messages=anthropic_msgs,
        )
        text = ""
        tool_calls: list[dict] = []
        for block in response.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text += block.text
            elif btype == "tool_use":
                tool_calls.append({"id": block.id, "name": block.name, "input": block.input or {}})
        return {
            "text": text,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason or "end_turn",
            # Pass full content back so we can build the next assistant message accurately.
            "raw_content": list(response.content),
        }


def _serialize_for_llm(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    try:
        return json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(payload)


def _filter_tools(role: RoleConfig) -> list[dict]:
    """Return the Anthropic-shaped tool schemas restricted to this role."""
    allowed = role.tool_set
    return [spec for spec in to_anthropic_format() if spec["name"] in allowed]


def _execute_tool(name: str, args: dict) -> tuple[Any, bool]:
    spec = get_tool(name)
    if spec is None:
        return ({"ok": False, "error": f"Unknown tool {name!r}"}, False)
    try:
        result = spec.fn(**args) if args else spec.fn()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Studio tool %s raised", name)
        return ({"ok": False, "error": str(exc), "error_type": type(exc).__name__}, False)
    ok = not (isinstance(result, dict) and result.get("ok") is False)
    return (result, ok)


class RoleRunner:
    """Drive one RoleConfig through a brief using a tool-calling loop."""

    def __init__(self, client: LLMClient, max_iterations: int = 8):
        self.client = client
        self.max_iterations = max_iterations

    def run(
        self,
        role: RoleConfig,
        brief: str,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
    ) -> RoleRunResult:
        tools = _filter_tools(role)
        if not tools:
            logger.warning("Role %s has no tools registered; LLM will just talk.", role.id)
        messages: list[dict] = [{"role": "user", "content": brief}]
        result = RoleRunResult(role_id=role.id, text="")

        for iteration in range(1, self.max_iterations + 1):
            response = self.client.complete(
                system=role.system_prompt,
                tools=tools,
                messages=messages,
            )
            result.iterations = iteration
            text = response.get("text", "") or ""
            tool_calls = response.get("tool_calls") or []
            stop_reason = response.get("stop_reason") or "end_turn"

            if text:
                result.text = (result.text + text).strip() if not result.text else result.text + "\n" + text

            if not tool_calls:
                result.stop_reason = stop_reason
                return result

            # Append the assistant turn (provider-neutral) so the LLM has its own history.
            assistant_content = response.get("raw_content")
            if assistant_content is None:
                assistant_content = [{"type": "text", "text": text}] if text else []
                for tc in tool_calls:
                    assistant_content.append(
                        {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
                    )
            messages.append({"role": "assistant", "content": assistant_content})

            for call in tool_calls:
                name = call["name"]
                args = call.get("input") or {}
                if on_tool_call:
                    try:
                        on_tool_call(name, args)
                    except Exception:
                        logger.exception("on_tool_call callback failed")

                payload, ok = _execute_tool(name, args)
                result.tool_calls.append(ToolCallRecord(name=name, input=args, result=payload, ok=ok))
                if on_tool_result:
                    try:
                        on_tool_result(name, payload)
                    except Exception:
                        logger.exception("on_tool_result callback failed")

                messages.append(
                    {
                        "role": "tool",
                        "tool_use_id": call["id"],
                        "content": _serialize_for_llm(payload),
                    }
                )

        result.stop_reason = "max_iterations"
        return result


def make_default_client(config: Config) -> LLMClient:
    """Pick the right LLM adapter based on Config.provider.

    Phase 2 ships an Anthropic adapter only — Ollama support follows once
    the role prompts are validated against Claude. Until then, Ollama
    config falls back to Anthropic IF an API key is present.
    """
    if config.provider == "anthropic" or config.api_key:
        return AnthropicClient(config)
    raise RuntimeError(
        "RoleRunner currently requires Anthropic. Set ANTHROPIC_API_KEY and "
        "UNITYTOOLS_PROVIDER=anthropic, or pass a custom LLMClient."
    )
