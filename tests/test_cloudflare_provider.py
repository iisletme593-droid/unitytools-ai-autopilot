"""Cloudflare Workers AI provider tests.

Cloudflare yanitlarinin hem OpenAI-uyumlu hem native /ai/run bicimini tolere
etmesi, tool-calling dongusunun calismasi ve config dogrulamasi test edilir.
HTTP cagrisi (`_cloudflare_chat`) monkeypatch ile script'lenir; gercek ag yok.
"""
from __future__ import annotations

import json

from unitytools.core.config import Config
from unitytools.core.orchestrator import Orchestrator
from unitytools.core.tool_registry import tool


# Bu modul import edilince registry'ye kaydolan bir test tool'u.
@tool(description="Echo test tool for Cloudflare provider tests")
def unity_cf_test_echo(value: str = "") -> dict:
    return {"ok": True, "echoed": value}


def _cf_config() -> Config:
    return Config(
        provider="cloudflare",
        cloudflare_account_id="acct123",
        cloudflare_api_token="tok456",
        cloudflare_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    )


def test_validation_requires_account_and_token():
    missing = Config(provider="cloudflare")
    problems = missing.validate()
    assert any("CLOUDFLARE_ACCOUNT_ID" in p for p in problems)
    assert any("CLOUDFLARE_API_TOKEN" in p for p in problems)

    ok = _cf_config()
    assert not any("CLOUDFLARE" in p for p in ok.validate())


def test_active_model_and_url():
    cfg = _cf_config()
    assert cfg.active_model() == "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    assert cfg.cloudflare_chat_url() == (
        "https://api.cloudflare.com/client/v4/accounts/acct123/ai/v1/chat/completions"
    )
    cfg.cloudflare_base_url = "https://gateway.example/v1/"
    assert cfg.cloudflare_chat_url() == "https://gateway.example/v1/chat/completions"


def test_coerce_tool_call_handles_all_shapes():
    # OpenAI shape (arguments as JSON string)
    openai = Orchestrator._coerce_tool_call(
        {"id": "x1", "type": "function",
         "function": {"name": "unity_cf_test_echo", "arguments": '{"value": "a"}'}}
    )
    assert openai["function"]["name"] == "unity_cf_test_echo"
    assert openai["function"]["arguments"] == '{"value": "a"}'
    assert openai["id"] == "x1"

    # Native shape (name + dict arguments, no nesting)
    native = Orchestrator._coerce_tool_call(
        {"name": "unity_cf_test_echo", "arguments": {"value": "b"}}
    )
    assert native["function"]["name"] == "unity_cf_test_echo"
    assert json.loads(native["function"]["arguments"]) == {"value": "b"}
    assert native["id"].startswith("call_")  # id uretildi

    # Gecersiz girdiler
    assert Orchestrator._coerce_tool_call({"arguments": {}}) is None
    assert Orchestrator._coerce_tool_call("not a dict") is None


def test_normalize_message_openai_and_native():
    orch = Orchestrator(_cf_config())

    content, calls = orch._cf_normalize_message(
        {"choices": [{"message": {"content": "hello",
         "tool_calls": [{"id": "c1", "type": "function",
                         "function": {"name": "unity_cf_test_echo", "arguments": "{}"}}]}}]}
    )
    assert content == "hello"
    assert calls[0]["function"]["name"] == "unity_cf_test_echo"

    content, calls = orch._cf_normalize_message(
        {"result": {"response": "native text",
         "tool_calls": [{"name": "unity_cf_test_echo", "arguments": {"value": "z"}}]}}
    )
    assert content == "native text"
    assert json.loads(calls[0]["function"]["arguments"]) == {"value": "z"}


def test_chat_cloudflare_runs_tool_then_finishes(monkeypatch):
    orch = Orchestrator(_cf_config())

    # 1. cagri: tool iste; 2. cagri: tool sonucunu gorup metinle bitir.
    scripted = [
        {"choices": [{"message": {
            "content": "",
            "tool_calls": [{"id": "call_1", "type": "function",
                            "function": {"name": "unity_cf_test_echo",
                                         "arguments": '{"value": "merhaba"}'}}]}}]},
        {"choices": [{"message": {"content": "Tamam, echo yapildi.", "tool_calls": []}}]},
    ]
    seen_payloads = []

    def fake_chat(messages, tools):
        seen_payloads.append([dict(m) for m in messages])
        return scripted[min(len(seen_payloads) - 1, len(scripted) - 1)]

    monkeypatch.setattr(orch, "_cloudflare_chat", fake_chat)

    tool_events = []
    result = orch.chat(
        "echo merhaba",
        on_tool_call=lambda n, i: tool_events.append((n, i)),
    )

    assert "echo yapildi" in result.text.lower()
    assert result.stop_reason == "stop"
    # Tool gercekten calisti
    assert tool_events == [("unity_cf_test_echo", {"value": "merhaba"})]
    assert any(c["name"] == "unity_cf_test_echo" and c["ok"] for c in result.tool_calls)
    # Gecmiste OpenAI-uyumlu tool result mesaji (tool_call_id ile) olusmus olmali
    tool_msgs = [m for m in orch.cf_messages if m.get("role") == "tool"]
    assert tool_msgs and tool_msgs[0]["tool_call_id"] == "call_1"


def test_chat_cloudflare_recovers_tool_call_from_text(monkeypatch):
    """Model yapisal tool_call yerine metne JSON gomerse kurtarilmali."""
    orch = Orchestrator(_cf_config())
    scripted = [
        {"choices": [{"message": {
            "content": '{"tool": "unity_cf_test_echo", "input": {"value": "x"}}',
            "tool_calls": []}}]},
        {"choices": [{"message": {"content": "bitti", "tool_calls": []}}]},
    ]
    calls = {"n": 0}

    def fake_chat(messages, tools):
        r = scripted[min(calls["n"], len(scripted) - 1)]
        calls["n"] += 1
        return r

    monkeypatch.setattr(orch, "_cloudflare_chat", fake_chat)
    result = orch.chat("metin icinde tool")
    assert any(c["name"] == "unity_cf_test_echo" for c in result.tool_calls)
