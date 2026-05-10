"""Phase 8 tests: OllamaClient with a mocked HTTP layer.

Validates:
- Provider dispatch in make_default_client (anthropic vs ollama)
- Message + tool translation between provider-neutral and Ollama format
- Structured tool_calls path (model returns OpenAI-compatible function calls)
- Text-fallback path (model emits JSON in content; we recover it)
- Model override propagates through make_default_client
- A round-trip: scripted Ollama responses drive a real RoleRunner loop
- HTTP errors surface as RuntimeError without crashing the runner
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.core.config import Config
from unitytools.studio import (
    DESIGNER,
    OllamaClient,
    RoleRunner,
    StudioPaths,
    StudioState,
    init_studio_tools,
    make_default_client,
)
from unitytools.studio.runner import _extract_text_tool_calls
import unitytools.studio.runner as runner_mod


# ───────────────────────────────────────────── helpers


def _ollama_config(model: str = "gemma4:latest") -> Config:
    return Config(
        api_key="",
        provider="ollama",
        ollama_host="http://127.0.0.1:11434",
        ollama_model=model,
    )


@contextmanager
def _patch_urlopen(responses):
    """Patch urllib.request.urlopen with a queue of canned responses.

    Each response can be:
      - dict        -> served as JSON, status 200
      - HTTPError   -> raised
      - URLError    -> raised
    """
    queue = list(responses)
    captured_requests: list[dict] = []
    original = urllib.request.urlopen

    def fake_urlopen(req, timeout=None):
        if hasattr(req, "data") and req.data:
            captured_requests.append(json.loads(req.data.decode("utf-8")))
        else:
            captured_requests.append({})
        if not queue:
            raise AssertionError("urlopen queue exhausted")
        item = queue.pop(0)
        if isinstance(item, urllib.error.URLError):
            raise item
        if isinstance(item, urllib.error.HTTPError):
            raise item
        return _FakeHttpResp(item)

    runner_mod.urllib.request.urlopen = fake_urlopen
    try:
        yield captured_requests
    finally:
        runner_mod.urllib.request.urlopen = original


class _FakeHttpResp:
    def __init__(self, payload):
        self._buf = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._buf

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="ollama-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ─────────────────────────────────────────────────── tests


def test_make_default_client_dispatches_by_provider() -> None:
    cfg_ollama = _ollama_config("gemma4:latest")
    client = make_default_client(cfg_ollama)
    assert isinstance(client, OllamaClient)
    assert client.model == "gemma4:latest"

    # Override wins
    client2 = make_default_client(cfg_ollama, model_override="qwen2.5:14b-instruct")
    assert isinstance(client2, OllamaClient)
    assert client2.model == "qwen2.5:14b-instruct"

    # Anthropic path still works (would error here without an api key, so
    # check that ollama provider isn't accidentally picked).
    cfg_no_provider = Config(api_key="", provider="anthropic")
    raised = False
    try:
        make_default_client(cfg_no_provider)
    except RuntimeError:
        raised = True
    assert raised, "anthropic path with no key must error, not silently fall back"
    print("OK make_default_client dispatch + override")


def test_ollama_translates_messages_and_tools() -> None:
    cfg = _ollama_config()
    client = OllamaClient(cfg)
    response = {
        "message": {
            "role": "assistant",
            "content": "All good.",
            "tool_calls": [],
        }
    }
    with _patch_urlopen([response]) as requests:
        result = client.complete(
            system="SYSTEM PROMPT",
            tools=[
                {
                    "name": "studio_get_summary",
                    "description": "Snapshot of studio state.",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
            messages=[{"role": "user", "content": "ping"}],
        )
    assert result["text"] == "All good."
    assert result["tool_calls"] == []
    assert result["stop_reason"] == "end_turn"

    # Inspect the request we sent
    sent = requests[0]
    assert sent["model"] == "gemma4:latest"
    assert sent["stream"] is False
    assert sent["messages"][0] == {"role": "system", "content": "SYSTEM PROMPT"}
    assert sent["messages"][1] == {"role": "user", "content": "ping"}
    # Tool format is OpenAI function shape
    assert sent["tools"][0]["type"] == "function"
    assert sent["tools"][0]["function"]["name"] == "studio_get_summary"
    print("OK Ollama request shape: messages + tools translated")


def test_ollama_structured_tool_calls_round_trip() -> None:
    cfg = _ollama_config()
    client = OllamaClient(cfg)
    response = {
        "message": {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "studio_read_gdd",
                        "arguments": {},
                    }
                }
            ],
        }
    }
    with _patch_urlopen([response]):
        result = client.complete(
            system="X",
            tools=[
                {
                    "name": "studio_read_gdd",
                    "description": "read gdd",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
            messages=[{"role": "user", "content": "hi"}],
        )
    assert result["stop_reason"] == "tool_use"
    assert len(result["tool_calls"]) == 1
    tc = result["tool_calls"][0]
    assert tc["name"] == "studio_read_gdd"
    assert tc["input"] == {}
    assert tc["id"].startswith("oll-")
    print("OK Ollama structured tool_calls translated to provider-neutral")


def test_ollama_text_fallback_recovers_tool_call_from_json() -> None:
    """Some Ollama models emit tool calls inline as JSON in `content`. The
    OllamaClient must recover them when `tool_calls` is empty."""
    cfg = _ollama_config()
    client = OllamaClient(cfg)
    response = {
        "message": {
            "role": "assistant",
            "content": '```json\n{"tool": "studio_get_summary", "input": {}}\n```',
            "tool_calls": [],
        }
    }
    with _patch_urlopen([response]):
        result = client.complete(
            system="X",
            tools=[
                {
                    "name": "studio_get_summary",
                    "description": "summary",
                    "input_schema": {"type": "object", "properties": {}},
                }
            ],
            messages=[{"role": "user", "content": "go"}],
        )
    assert result["stop_reason"] == "tool_use"
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "studio_get_summary"
    assert result["text"] == ""  # recovered text consumed
    print("OK Ollama text-fallback recovers tool call")


def test_ollama_extract_helper_only_accepts_registered_names() -> None:
    """The text-fallback must not invent tool names that aren't real;
    otherwise it would happily dispatch hallucinated tools."""
    text = '{"tool": "made_up_tool", "input": {}}'
    out = _extract_text_tool_calls(text, registered_names=set())
    assert out == []
    out = _extract_text_tool_calls(text, registered_names={"made_up_tool"})
    assert len(out) == 1 and out[0]["function"]["name"] == "made_up_tool"
    print("OK text-fallback gates by registered names")


def test_ollama_serialises_assistant_tool_results_back_to_provider() -> None:
    """Round-trip: assistant turn (with tool_use blocks) plus a tool-result
    user turn must translate into Ollama-compatible messages."""
    cfg = _ollama_config()
    client = OllamaClient(cfg)
    response = {"message": {"content": "final answer", "tool_calls": []}}
    with _patch_urlopen([response]) as requests:
        client.complete(
            system="S",
            tools=[],
            messages=[
                {"role": "user", "content": "first"},
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "thinking..."},
                        {
                            "type": "tool_use",
                            "id": "t1",
                            "name": "studio_get_summary",
                            "input": {},
                        },
                    ],
                },
                {"role": "tool", "tool_use_id": "t1", "content": '{"ok": true}'},
            ],
        )
    sent_messages = requests[0]["messages"]
    # system, user, assistant (with tool_calls), tool
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[1] == {"role": "user", "content": "first"}
    asst = sent_messages[2]
    assert asst["role"] == "assistant"
    assert asst["content"] == "thinking..."
    assert asst["tool_calls"][0]["function"]["name"] == "studio_get_summary"
    assert sent_messages[3]["role"] == "tool"
    assert sent_messages[3]["content"] == '{"ok": true}'
    print("OK assistant + tool turns translated correctly")


def test_ollama_full_runner_loop_with_real_studio_tools() -> None:
    """Drive the full RoleRunner with a scripted Ollama. The Designer
    should call studio_read_gdd, then studio_write_gdd, then end."""
    state, _ = _fresh_studio()
    cfg = _ollama_config()
    client = OllamaClient(cfg)

    # Three turns: read, write, end
    responses = [
        {
            "message": {
                "content": "",
                "tool_calls": [{"function": {"name": "studio_read_gdd", "arguments": {}}}],
            }
        },
        {
            "message": {
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "studio_write_gdd",
                            "arguments": {"content": "# GDD\nwritten via Ollama.\n"},
                        }
                    }
                ],
            }
        },
        {"message": {"content": "GDD updated.", "tool_calls": []}},
    ]
    with _patch_urlopen(responses):
        runner = RoleRunner(client, max_iterations=5)
        result = runner.run(DESIGNER, brief="Run via fake Ollama.")
    assert result.stop_reason == "end_turn"
    assert [tc.name for tc in result.tool_calls] == ["studio_read_gdd", "studio_write_gdd"]
    assert "written via Ollama" in state.read_doc(state.paths.gdd)
    print("OK full RoleRunner round-trip with mocked Ollama")


def test_ollama_http_error_surfaces_as_runtime_error() -> None:
    cfg = _ollama_config()
    client = OllamaClient(cfg)
    err = urllib.error.HTTPError(
        url=cfg.ollama_host + "/api/chat",
        code=500,
        msg="server err",
        hdrs=None,
        fp=io.BytesIO(b'{"error": "model not found"}'),
    )
    with _patch_urlopen([err]):
        raised = False
        try:
            client.complete(system="x", tools=[], messages=[{"role": "user", "content": "go"}])
        except RuntimeError as exc:
            raised = True
            assert "Ollama HTTP" in str(exc)
        assert raised
    print("OK HTTP errors raise RuntimeError, not silent failure")


def test_ollama_unreachable_host_surfaces_as_runtime_error() -> None:
    cfg = _ollama_config()
    client = OllamaClient(cfg)
    with _patch_urlopen([urllib.error.URLError("Connection refused")]):
        raised = False
        try:
            client.complete(system="x", tools=[], messages=[{"role": "user", "content": "go"}])
        except RuntimeError as exc:
            raised = True
            assert "Ollama not reachable" in str(exc)
        assert raised
    print("OK unreachable Ollama host raises clear RuntimeError")


def test_ollama_requires_model() -> None:
    cfg = Config(api_key="", provider="ollama", ollama_model="")
    raised = False
    try:
        OllamaClient(cfg)
    except RuntimeError as exc:
        raised = True
        assert "model" in str(exc).lower()
    assert raised
    print("OK OllamaClient refuses construction without a model")


def run_test() -> None:
    test_make_default_client_dispatches_by_provider()
    test_ollama_translates_messages_and_tools()
    test_ollama_structured_tool_calls_round_trip()
    test_ollama_text_fallback_recovers_tool_call_from_json()
    test_ollama_extract_helper_only_accepts_registered_names()
    test_ollama_serialises_assistant_tool_results_back_to_provider()
    test_ollama_full_runner_loop_with_real_studio_tools()
    test_ollama_http_error_surfaces_as_runtime_error()
    test_ollama_unreachable_host_surfaces_as_runtime_error()
    test_ollama_requires_model()
    print("All Phase 8 Ollama tests passed")


if __name__ == "__main__":
    run_test()
