"""Anthropic 400 kilidi regresyon testleri.

Bozuk history (yetim tool_use, boş content, eşleşmeyen tool_result) Anthropic'ten
400 döndürür. Eski davranışta bozuk mesajlar history'de kaldığı için her sonraki
istek de 400 alır ve sohbet kalıcı kilitlenirdi. Yeni davranış:
  1. 400 gelince history onarılır ve istek bir kez tekrarlanır.
  2. Hâlâ 400 ise bozuk tur geri alınır; sonraki mesajlar temiz history ile çalışır.
  3. Tool çalıştırma yarıda kesilse bile her tool_use'a bir tool_result eşlenir.
"""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from anthropic import BadRequestError

from unitytools.core.config import Config
from unitytools.core.orchestrator import ChatMessage, Orchestrator


def _bad_request(msg: str = "invalid request") -> BadRequestError:
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    resp = httpx.Response(400, request=req)
    return BadRequestError(msg, response=resp, body={"error": {"message": msg}})


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(block_id: str, name: str = "unity_ping") -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=block_id, name=name, input={})


def _response(content, stop_reason="end_turn"):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class FakeMessages:
    """Sıradaki öğe exception ise fırlatır, değilse yanıt olarak döner."""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.calls: list[list[dict]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs["messages"])
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _make_orchestrator(script: list) -> tuple[Orchestrator, FakeMessages]:
    cfg = Config(provider="anthropic", api_key="sk-ant-test")
    orch = Orchestrator(cfg)
    fake = FakeMessages(script)
    orch.client = SimpleNamespace(messages=fake)
    return orch, fake


def test_dangling_tool_use_repaired_then_retried():
    """Yetim tool_use 400 tetikler; onarım + retry sohbeti kurtarmalı."""
    orch, fake = _make_orchestrator(
        [_bad_request("tool_use without tool_result"), _response([_text_block("tamam")])]
    )
    # Önceki oturumdan yarıda kalmış bir tur: tool_result'sız tool_use.
    orch.history = [
        ChatMessage(role="user", content="ağaç ekle"),
        ChatMessage(role="assistant", content=[_tool_use_block("tu_1")]),
    ]
    result = orch.chat("devam et")
    assert result.text == "tamam"
    # Onarım yetim tool_use'a sentetik tool_result eklemiş olmalı.
    retry_messages = fake.calls[-1]
    tool_results = [
        m for m in retry_messages
        if m["role"] == "user" and isinstance(m["content"], list)
        and m["content"] and m["content"][0].get("type") == "tool_result"
    ]
    assert any(
        b["tool_use_id"] == "tu_1" for m in tool_results for b in m["content"]
    )


def test_persistent_400_rolls_back_turn_so_chat_is_not_locked():
    """Onarım işe yaramazsa tur geri alınmalı; sonraki mesaj temiz başlamalı."""
    orch, fake = _make_orchestrator(
        [
            _bad_request("oversized"),
            _bad_request("oversized"),  # onarım sonrası retry de 400
            _response([_text_block("merhaba")]),
        ]
    )
    # Geçmişte onarılabilir görünen bir bozukluk olsun ki retry tetiklensin.
    orch.history = [ChatMessage(role="assistant", content=[_tool_use_block("tu_x")])]
    with pytest.raises(RuntimeError, match="400"):
        orch.chat("kocaman bir istek")
    # Bozuk tur history'de KALMAMALI (eski davranış: kalıcı kilit).
    assert all(m.content != "kocaman bir istek" for m in orch.history)
    # Sohbet kilitlenmemiş olmalı: yeni mesaj normal yanıt alır.
    result = orch.chat("merhaba de")
    assert result.text == "merhaba"


def test_empty_content_response_not_appended_to_history():
    orch, _ = _make_orchestrator([_response([], stop_reason="end_turn")])
    orch.chat("selam")
    assert all(m.content for m in orch.history if m.role == "assistant")


def test_interrupted_tool_execution_leaves_paired_history():
    """KeyboardInterrupt tool çalıştırmayı kesse bile tool_use yanıtsız kalmamalı."""
    orch, _ = _make_orchestrator(
        [_response([_tool_use_block("tu_int")], stop_reason="tool_use")]
    )

    def boom(name, params):
        raise KeyboardInterrupt()

    orch._execute_tool = boom
    with pytest.raises(KeyboardInterrupt):
        orch.chat("bir şey yap")
    last = orch.history[-1]
    assert last.role == "user"
    assert last.content[0]["type"] == "tool_result"
    assert last.content[0]["tool_use_id"] == "tu_int"


def test_repair_drops_orphan_tool_results_and_empty_messages():
    orch, _ = _make_orchestrator([])
    orch.history = [
        ChatMessage(role="user", content=""),  # boş -> düşmeli
        ChatMessage(role="user", content="gerçek mesaj"),
        ChatMessage(role="assistant", content=[_text_block("cevap")]),
        # Eşleşen tool_use'u olmayan tool_result -> düşmeli
        ChatMessage(
            role="user",
            content=[{"type": "tool_result", "tool_use_id": "hayalet", "content": "x"}],
        ),
    ]
    assert orch._repair_anthropic_history() is True
    contents = [m.content for m in orch.history]
    assert "gerçek mesaj" in contents
    assert len(orch.history) == 2
