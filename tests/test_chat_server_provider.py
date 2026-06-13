"""chat-server dual-agent / provider secim mantigi testleri."""
from __future__ import annotations

from unitytools.cli.entry import _dual_agent_allowed


def test_dual_agent_only_for_ollama():
    assert _dual_agent_allowed("ollama") is True
    assert _dual_agent_allowed("cloudflare") is False
    assert _dual_agent_allowed("anthropic") is False
    assert _dual_agent_allowed("") is False
