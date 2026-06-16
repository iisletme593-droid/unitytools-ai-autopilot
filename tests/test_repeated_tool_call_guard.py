"""P0: orchestrator, model ayni tool cagrisini tekrar ederse durmali (over-creation fix)."""
from unitytools.core.config import Config
from unitytools.core.orchestrator import Orchestrator


def _orch_cloudflare():
    c = Config()
    c.provider = "cloudflare"
    c.cloudflare_account_id = "acct"
    c.cloudflare_api_token = "tok"
    return Orchestrator(c)


def test_repeated_identical_tool_calls_stop():
    o = _orch_cloudflare()
    o._select_ollama_tools = lambda msg: []
    # Backend her seferinde AYNI tool cagrisini ister (donguye giren model).
    o._cloudflare_chat = lambda messages, tools, model=None: {
        "message": {"content": "", "tool_calls": [{"name": "noop_tool", "arguments": {"x": 1}}]}
    }
    calls = {"n": 0}

    def fake_exec(name, params):
        calls["n"] += 1
        return {"ok": True}

    o._execute_tool = fake_exec
    r = o.chat("ayni seyi tekrar tekrar yap", max_iterations=10)
    # Eylem yalnizca BIR kez calismali, sonra durmali (10 kez degil).
    assert calls["n"] == 1, f"tool {calls['n']} kez calisti, beklenen 1"
    assert r.stop_reason == "repeated_tool_calls", r.stop_reason


def test_distinct_tool_calls_not_blocked():
    """Farkli parametreli cagrilar engellenMEmeli (mesru cok-nesne)."""
    o = _orch_cloudflare()
    o._select_ollama_tools = lambda msg: []
    seq = [
        {"message": {"content": "", "tool_calls": [{"name": "make", "arguments": {"i": 1}}]}},
        {"message": {"content": "", "tool_calls": [{"name": "make", "arguments": {"i": 2}}]}},
        {"message": {"content": "tamamlandi", "tool_calls": []}},
    ]
    box = {"k": 0}

    def backend(messages, tools, model=None):
        out = seq[min(box["k"], len(seq) - 1)]
        box["k"] += 1
        return out

    o._cloudflare_chat = backend
    calls = {"n": 0}
    o._execute_tool = lambda name, params: (calls.__setitem__("n", calls["n"] + 1), {"ok": True})[1]
    r = o.chat("iki farkli nesne yap", max_iterations=10)
    assert calls["n"] == 2, f"tool {calls['n']} kez calisti, beklenen 2"
    assert r.stop_reason == "stop", r.stop_reason
