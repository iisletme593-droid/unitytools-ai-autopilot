"""RoleRunner — drive a single role agent through one brief.

This is a narrower tool-calling loop than core/orchestrator.py: it
takes a RoleConfig, hands the LLM only that role's allowed tools and
its dedicated system prompt, runs the loop until the model stops
producing tool calls, and returns the final text plus a tool-call log.

The LLM call is injected via a `LLMClient` protocol so tests can swap a
deterministic fake without monkey-patching anthropic / urllib.

Provider support: AnthropicClient (Claude, vision) and OllamaClient
(local Gemma / Qwen / Llama; tool calling via OpenAI-compatible
function format with a text-fallback for models that emit tool calls
as JSON in the assistant message).
"""
from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional, Protocol

from ..core.config import Config
from ..core.tool_registry import get_tool, to_anthropic_format
from .roles import RoleConfig

if TYPE_CHECKING:
    from .state import StudioState  # noqa: F401 (used in type hints only)

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
        usage = getattr(response, "usage", None)
        usage_block: Optional[dict] = None
        if usage is not None:
            usage_block = {
                "model": self._model,
                "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
            }
        return {
            "text": text,
            "tool_calls": tool_calls,
            "stop_reason": response.stop_reason or "end_turn",
            # Pass full content back so we can build the next assistant message accurately.
            "raw_content": list(response.content),
            "usage": usage_block,
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


def _execute_tool(name: str, args: dict, allowed: Optional[set[str]] = None) -> tuple[Any, bool]:
    """Execute one tool call.

    `allowed` is the role's tool whitelist. The runner only advertises
    these to the LLM, but a confused or adversarial model may still emit
    a tool_call for something else (hallucination from training data,
    schema confusion). We refuse to dispatch outside the allowlist so
    the role's sandbox is enforced at the *execution* layer too.
    """
    if allowed is not None and name not in allowed:
        logger.warning("Refusing tool call %r — not in role allowlist", name)
        return (
            {"ok": False, "error": f"Tool {name!r} is not allowed for this role.", "error_type": "ToolNotAllowed"},
            False,
        )
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
    """Drive one RoleConfig through a brief using a tool-calling loop.

    Phase 33: when `state` is provided and the LLMClient returns a
    `usage` block, each round's tokens get appended to
    studio/qa/cost_log.jsonl for the studio_cost_summary tool. Tests
    that pass a FakeLLM without usage are unaffected.
    """

    def __init__(
        self,
        client: LLMClient,
        max_iterations: int = 8,
        state: Optional["StudioState"] = None,
    ):
        self.client = client
        self.max_iterations = max_iterations
        self.state = state

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

            # Phase 33: append a cost row when the client returned usage
            # and we have a StudioState to write into. Silently skips for
            # FakeLLM / RehearsalLLM tests.
            usage = response.get("usage")
            if usage and self.state is not None:
                try:
                    from .cost import append_cost_entry
                    append_cost_entry(
                        self.state,
                        role_id=role.id,
                        model=str(usage.get("model", "")),
                        input_tokens=int(usage.get("input_tokens", 0)),
                        output_tokens=int(usage.get("output_tokens", 0)),
                    )
                except Exception:
                    logger.exception("Cost log append failed (non-fatal)")

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

                payload, ok = _execute_tool(name, args, allowed=role.tool_set)
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


# ─── Ollama adapter (Phase 8) ──────────────────────────────────────────


def _extract_text_tool_calls(text: str, registered_names: set[str]) -> list[dict]:
    """Recover tool calls from raw text when a local model prints JSON
    instead of using its structured tool-call channel.

    Scans for fenced ```json blocks, top-level JSON objects, and inline
    {...} objects whose first key is one of "tool" / "name" / "function" /
    "tool_calls". Returns Ollama-shape calls (with "function" key); the
    caller normalises further. Tool names are gated by the registry to
    avoid greedy false positives.
    """
    if not text:
        return []
    candidates: list[str] = []
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", text, re.DOTALL | re.IGNORECASE))
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        candidates.append(stripped)
    candidates.extend(
        re.findall(r"(\{[^{}]*(?:\"tool\"|\"name\"|\"tool_calls\"|\"function\")[\s\S]*?\})", text)
    )

    out: list[dict] = []
    for raw in candidates:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        rows: list = payload if isinstance(payload, list) else [payload]
        if isinstance(payload, dict) and isinstance(payload.get("tool_calls"), list):
            rows = payload["tool_calls"]
        for row in rows:
            if not isinstance(row, dict):
                continue
            fn = row.get("function") if isinstance(row.get("function"), dict) else {}
            name = fn.get("name") or row.get("tool") or row.get("name") or row.get("tool_name")
            if not isinstance(name, str) or name not in registered_names:
                continue
            args = (
                fn.get("arguments")
                if "arguments" in fn
                else row.get("input", row.get("arguments", row.get("params", {})))
            )
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except json.JSONDecodeError:
                    args = {}
            if not isinstance(args, dict):
                args = {}
            out.append({"function": {"name": name, "arguments": args}})
        if out:
            break
    return out


class OllamaClient:
    """LLMClient backed by a local Ollama server.

    Handles the OpenAI-compatible tool-call format Ollama exposes via
    /api/chat. Translates between provider-neutral message blocks and
    Ollama's `messages` array (with assistant tool_calls / tool result
    rounds). Falls back to text extraction when the model emits tool
    calls as JSON in the assistant content (Qwen / older Gemma do this).
    """

    def __init__(
        self,
        config: Config,
        model_override: Optional[str] = None,
        timeout: float = 180.0,
        num_ctx: int = 8192,
    ):
        self._host = config.ollama_host.rstrip("/")
        self._model = model_override or config.ollama_model
        if not self._model:
            raise RuntimeError("OllamaClient requires a model (set OLLAMA_MODEL or pass model_override).")
        self._timeout = float(timeout)
        self._num_ctx = int(num_ctx)

    @property
    def model(self) -> str:
        return self._model

    def complete(self, system: str, tools: list[dict], messages: list[dict]) -> dict:
        ollama_messages = self._translate_messages(system, messages)
        ollama_tools = self._translate_tools(tools)
        body: dict[str, Any] = {
            "model": self._model,
            "messages": ollama_messages,
            "stream": False,
            "options": {"num_ctx": self._num_ctx},
        }
        if ollama_tools:
            body["tools"] = ollama_tools

        data = self._post_chat(body)
        msg = data.get("message") or {}
        text = msg.get("content") or ""
        tool_calls_raw = msg.get("tool_calls") or []

        # Fallback: model embedded tool calls in plain text
        if not tool_calls_raw and text:
            registered = {t["name"] for t in tools}
            text_extracted = _extract_text_tool_calls(text, registered)
            if text_extracted:
                tool_calls_raw = text_extracted
                text = ""  # consumed by the extraction

        tool_calls: list[dict] = []
        for i, call in enumerate(tool_calls_raw):
            fn = call.get("function") if isinstance(call.get("function"), dict) else {}
            name = fn.get("name") or call.get("name") or ""
            args = fn.get("arguments")
            if args is None:
                args = call.get("arguments") or call.get("input") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except json.JSONDecodeError:
                    args = {}
            if not isinstance(args, dict):
                args = {}
            tool_calls.append({"id": call.get("id") or f"oll-{i}", "name": name, "input": args})

        # Ollama returns prompt_eval_count + eval_count (request + response token counts)
        # when streaming is off. Surface these so the studio's cost log records
        # local-model usage at $0 cost (still visible).
        prompt_toks = int(data.get("prompt_eval_count") or 0)
        eval_toks = int(data.get("eval_count") or 0)
        return {
            "text": text,
            "tool_calls": tool_calls,
            "stop_reason": "tool_use" if tool_calls else "end_turn",
            "raw_content": None,
            "usage": {
                "model": self._model,
                "input_tokens": prompt_toks,
                "output_tokens": eval_toks,
            } if (prompt_toks or eval_toks) else None,
        }

    # ---- translation helpers ----

    @staticmethod
    def _translate_messages(system: str, messages: list[dict]) -> list[dict]:
        out: list[dict] = [{"role": "system", "content": system}]
        for m in messages:
            role = m.get("role")
            if role == "tool":
                out.append({"role": "tool", "content": m.get("content", "")})
                continue
            if role == "assistant":
                content = m.get("content")
                if isinstance(content, list):
                    text_parts: list[str] = []
                    tool_calls: list[dict] = []
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            text_parts.append(block.get("text", ""))
                        elif btype == "tool_use":
                            tool_calls.append(
                                {
                                    "function": {
                                        "name": block.get("name", ""),
                                        "arguments": block.get("input") or {},
                                    },
                                }
                            )
                    flat: dict[str, Any] = {"role": "assistant", "content": "".join(text_parts)}
                    if tool_calls:
                        flat["tool_calls"] = tool_calls
                    out.append(flat)
                else:
                    out.append({"role": "assistant", "content": content or ""})
                continue
            # user / system
            content = m.get("content")
            if isinstance(content, list):
                # Flatten any text blocks; drop image blocks (Ollama vision is
                # provider-specific; doc-only roles never carry images here).
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                content = "".join(text_parts)
            out.append({"role": role or "user", "content": content or ""})
        return out

    @staticmethod
    def _translate_tools(tools: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    def _post_chat(self, body: dict) -> dict:
        req = urllib.request.Request(
            f"{self._host}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                err_body = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                err_body = ""
            raise RuntimeError(f"Ollama HTTP {exc.code}: {err_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Ollama not reachable at {self._host}: {exc}. "
                "Start Ollama (`ollama serve`) or set OLLAMA_HOST."
            ) from exc


def make_default_client(config: Config, model_override: Optional[str] = None) -> LLMClient:
    """Pick the right LLM adapter based on Config.provider.

    - provider == "anthropic" (or any provider when only ANTHROPIC_API_KEY
      is set) -> AnthropicClient (vision-capable).
    - provider == "ollama" -> OllamaClient (local model, tool calling
      via OpenAI-compatible function format with a text-fallback).

    `model_override` lets a per-role caller swap the model without
    mutating Config (e.g. a Worker on Qwen 14b, a Designer on Gemma 4 8b).
    """
    if config.provider == "ollama":
        return OllamaClient(config, model_override=model_override)
    if config.provider == "anthropic" or config.api_key:
        return AnthropicClient(config)
    raise RuntimeError(
        "No LLM provider configured. Set UNITYTOOLS_PROVIDER=ollama (with OLLAMA_MODEL) "
        "or UNITYTOOLS_PROVIDER=anthropic (with ANTHROPIC_API_KEY)."
    )


# ─── Rehearsal (dry-run) LLM ───────────────────────────────────────────


# Per-role canned tool sequences used by dry-run mode. Each entry is one
# scripted "turn"; None marks the terminating turn (no tool calls, end of
# rehearsal). Engine-aware roles intentionally have NO script here — without
# a real Unity bridge they would write garbage; if you must rehearse them,
# inject a fake bridge plus a custom RehearsalLLM script.
_REHEARSAL_SCRIPTS: dict[str, list[Optional[dict]]] = {
    "producer": [
        {"name": "studio_get_summary", "input": {}},
        {"name": "studio_list_tasks", "input": {}},
        {"name": "studio_list_decisions", "input": {"limit": 10}},
        None,
    ],
    "designer": [
        {"name": "studio_get_summary", "input": {}},
        {"name": "studio_read_gdd", "input": {}},
        # If the GDD is empty, fill it with a placeholder so the next pass
        # has something concrete to react to.
        {
            "name": "studio_write_gdd",
            "input": {
                "content": (
                    "# Game Design Document\n\n"
                    "## 1. Pitch\n"
                    "_(rehearsal placeholder — replace with a real pitch)_\n\n"
                    "## 2. Core Loop\n"
                    "_(rehearsal placeholder)_\n\n"
                    "## 3. Pillars\n"
                    "- _(rehearsal placeholder)_\n"
                ),
            },
        },
        None,
    ],
    "critic": [
        {"name": "studio_get_summary", "input": {}},
        {"name": "studio_read_gdd", "input": {}},
        {"name": "studio_list_decisions", "input": {"limit": 20}},
        None,
    ],
}


class RehearsalLLM:
    """Deterministic, no-network LLM for dry-run mode.

    Plays a per-role canned tool sequence so a user without an API key
    can still wire up a project, see the workflow execute end-to-end,
    and verify disk state changes. NOT a substitute for a real run —
    its tool calls are template-grade, not project-aware.
    """

    def __init__(self, role_id: str):
        self.role_id = role_id
        self._script: list[Optional[dict]] = list(_REHEARSAL_SCRIPTS.get(role_id, []))
        self._cursor = 0
        self.calls: int = 0

    def complete(self, system: str, tools: list[dict], messages: list[dict]) -> dict:
        self.calls += 1
        if not self._script or self._cursor >= len(self._script):
            return {
                "text": (
                    f"[rehearsal: role {self.role_id!r} has no scripted actions. "
                    "Run with a real LLM client for meaningful work.]"
                ),
                "tool_calls": [],
                "stop_reason": "end_turn",
                "raw_content": None,
            }
        step = self._script[self._cursor]
        self._cursor += 1
        if step is None:
            return {
                "text": (
                    f"[rehearsal complete: {self._cursor - 1} scripted tool calls played for "
                    f"role {self.role_id!r}. Disk state should reflect the rehearsal.]"
                ),
                "tool_calls": [],
                "stop_reason": "end_turn",
                "raw_content": None,
            }
        # Defensive: skip calls that the role's own allowlist won't permit.
        # The runner will refuse them anyway, but that's a wasted round-trip.
        advertised = {t["name"] for t in tools}
        if step["name"] not in advertised:
            logger.warning(
                "Rehearsal step %r skipped — tool not advertised to role %r",
                step["name"],
                self.role_id,
            )
            # Skip ahead: re-issue complete() recursively via a synthetic step.
            return self.complete(system, tools, messages)
        return {
            "text": "",
            "tool_calls": [{"id": f"reh-{self._cursor}", "name": step["name"], "input": dict(step.get("input", {}))}],
            "stop_reason": "tool_use",
            "raw_content": None,
        }


def has_rehearsal_for(role_id: str) -> bool:
    """Whether dry-run mode has a canned script for this role."""
    return role_id in _REHEARSAL_SCRIPTS
