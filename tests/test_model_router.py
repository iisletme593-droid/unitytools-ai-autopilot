"""Cloudflare model router: a deterministic, code-derived task->model picker.

A catalog of task-specialised Cloudflare Workers AI models (ids verified against
developers.cloudflare.com) + select_model() which routes a chat message to the best
model. Chat-controllable (explicit override) with auto-detection; tool-requiring turns
always get a verified tool-capable model so the Unity tool-loop never breaks.
"""
import pytest

from unitytools.core.model_router import (
    MODEL_CATALOG, DEFAULT_MODEL, DEFAULT_TASK, _LIVE_TASKS,
    detect_task_type, parse_model_override, select_model, list_models,
    build_model_router_report,
)


class _Cfg:
    def __init__(self, model="@cf/openai/gpt-oss-120b", auto=True):
        self.cloudflare_model = model
        self.cloudflare_auto_route = auto


# --- catalog integrity (the verified ids must not silently change) ----------

VERIFIED = {
    "reasoning": ("@cf/openai/gpt-oss-120b", True, True),
    "general":   ("@cf/meta/llama-3.3-70b-instruct-fp8-fast", True, True),
    "coding":    ("@cf/qwen/qwen2.5-coder-32b-instruct", False, True),
    "creative":  ("@cf/zai-org/glm-4.7-flash", True, True),
    "fast":      ("@cf/meta/llama-3.1-8b-instruct-fast", False, True),
    "vision":    ("@cf/meta/llama-3.2-11b-vision-instruct", True, False),
    "image":     ("@cf/black-forest-labs/flux-1-schnell", False, False),
}


@pytest.mark.parametrize("task,expected", VERIFIED.items())
def test_catalog_has_the_verified_models(task, expected):
    model, tools, live = expected
    spec = MODEL_CATALOG[task]
    assert spec["model"] == model
    assert spec["tools"] is tools
    assert spec["live"] is live


def test_default_is_the_tool_capable_reasoning_model():
    assert DEFAULT_TASK == "reasoning"
    assert DEFAULT_MODEL == "@cf/openai/gpt-oss-120b"
    assert MODEL_CATALOG[DEFAULT_TASK]["tools"] is True


def test_live_tasks_are_the_five_text_chat_ones():
    assert set(_LIVE_TASKS) == {"coding", "creative", "reasoning", "fast", "general"}
    for t in _LIVE_TASKS:
        assert MODEL_CATALOG[t]["live"] is True and MODEL_CATALOG[t]["chat"] is True


# --- task detection ---------------------------------------------------------

@pytest.mark.parametrize("text,task", [
    ("bana bir hikaye yaz", "creative"),
    ("write me a short story with dialogue", "creative"),
    ("bu python fonksiyonundaki hatayi ayikla", "coding"),
    ("refactor this code and fix the bug", "coding"),
    ("adim adim dusun ve mantikli coz", "reasoning"),
    ("reason step by step about this", "reasoning"),
    ("bunu kisaca ozetle", "fast"),
    ("quickly classify this", "fast"),
    ("merhaba nasilsin", "general"),
    ("can you explain this in general", "general"),
])
def test_detect_task_type(text, task):
    assert detect_task_type(text) == task


def test_detect_defaults_to_general():
    assert detect_task_type("xyzzy plugh") == "general"


# --- explicit override ------------------------------------------------------

@pytest.mark.parametrize("text,task", [
    ("coder modeliyle bu kodu yaz", "coding"),
    ("use the creative model please", "creative"),
    ("hizli model ile siniflandir", "fast"),
    ("model: reasoning", "reasoning"),
    ("genel model kullan", "general"),
])
def test_parse_model_override(text, task):
    assert parse_model_override(text) == task


def test_override_by_raw_model_id():
    assert parse_model_override("lutfen @cf/qwen/qwen2.5-coder-32b-instruct kullan") == "coding"


def test_no_override_when_no_cue():
    assert parse_model_override("bana bir hikaye yaz") is None


# --- select_model: routing + safety -----------------------------------------

def test_tool_turns_always_get_a_tool_capable_model():
    # an action/Unity request: must route to a verified tool-capable model regardless
    # of what the text looks like (e.g. even a "code"-ish action)
    for text in ["arena oyunu kur 5 dusman", "build a scene", "kodla bir oyun yap"]:
        r = select_model(text, needs_tools=True, config=_Cfg())
        assert MODEL_CATALOG[r["task"]]["tools"] is True
        assert r["model"] == "@cf/openai/gpt-oss-120b"


def test_non_tool_chat_routes_by_task():
    assert select_model("bir hikaye yaz", needs_tools=False, config=_Cfg())["task"] == "creative"
    assert select_model("debug this function", needs_tools=False, config=_Cfg())["task"] == "coding"


def test_override_wins_over_auto():
    r = select_model("coder modeliyle yardim et", needs_tools=False, config=_Cfg())
    assert r["task"] == "coding" and r["routed"] is True


def test_non_tool_override_is_upgraded_when_tools_needed():
    # "coder" has no tools; if the turn needs tools the loop must stay working
    r = select_model("coder modeliyle arena oyunu kur", needs_tools=True, config=_Cfg())
    assert r["model"] == DEFAULT_MODEL and MODEL_CATALOG[r["task"]]["tools"] is True


def test_vision_image_overrides_never_break_the_text_loop():
    # vision/image are not live; an override to them falls back to a usable model
    for text in ["image modeliyle ciz", "vision modeli kullan"]:
        r = select_model(text, needs_tools=False, config=_Cfg())
        assert MODEL_CATALOG[r["task"]]["live"] is True


def test_auto_route_off_uses_configured_model():
    r = select_model("bir hikaye yaz", needs_tools=False, config=_Cfg(model="@cf/x/y", auto=False))
    assert r["model"] == "@cf/x/y" and r["routed"] is False


def test_live_routing_never_selects_vision_or_image():
    samples = ["resmi anlat", "gorsel olustur", "ciz bir manzara", "describe image", "draw a cat"]
    for text in samples:
        for nt in (True, False):
            r = select_model(text, needs_tools=nt, config=_Cfg())
            assert MODEL_CATALOG[r["task"]]["live"] is True       # only live text models


def test_select_model_is_deterministic():
    a = select_model("adim adim dusun", needs_tools=False, config=_Cfg())
    b = select_model("adim adim dusun", needs_tools=False, config=_Cfg())
    assert a == b


# --- list + report ----------------------------------------------------------

def test_list_models_live_only_drops_vision_and_image():
    live = {m["task"] for m in list_models(live_only=True)}
    assert "vision" not in live and "image" not in live
    assert live == set(_LIVE_TASKS)


def test_report_is_pure_ascii_and_lists_the_models():
    rep = build_model_router_report()
    assert all(ord(c) < 128 for c in rep)
    for spec in MODEL_CATALOG.values():
        assert spec["model"] in rep
    assert "CLOUDFLARE_AUTO_ROUTE=0" in rep            # documents the off-switch


# --- orchestrator wiring ----------------------------------------------------

def _orch():
    from unitytools.core.config import Config
    from unitytools.core.orchestrator import Orchestrator
    c = Config()
    c.provider = "cloudflare"
    c.cloudflare_account_id = "acct"
    c.cloudflare_api_token = "tok"
    return Orchestrator(c)


def test_orchestrator_routes_a_creative_chat_to_the_creative_model():
    o = _orch()
    o._select_ollama_tools = lambda msg: []           # no tools -> route by task
    captured = {}

    def backend(messages, tools, model=None):
        captured["model"] = model
        return {"message": {"content": "bir varmis bir yokmus", "tool_calls": []}}

    o._cloudflare_chat = backend
    o.chat("bana bir hikaye yaz", max_iterations=1)
    assert captured["model"] == "@cf/zai-org/glm-4.7-flash"


def test_orchestrator_routes_a_tool_turn_to_the_tool_capable_model():
    o = _orch()
    o._select_ollama_tools = lambda msg: [{"type": "function", "function": {"name": "x"}}]
    captured = {}

    def backend(messages, tools, model=None):
        captured["model"] = model
        return {"message": {"content": "ok", "tool_calls": []}}

    o._cloudflare_chat = backend
    o.chat("arena oyunu kur 5 dusman", max_iterations=1)
    assert captured["model"] == "@cf/openai/gpt-oss-120b"   # tool-capable, verified


# --- dual-agent role -> model ----------------------------------------------

def test_model_for_role_maps_each_agent_to_a_fitting_model():
    from unitytools.core.model_router import model_for_role
    assert model_for_role("master") == "@cf/openai/gpt-oss-120b"            # reasoning
    assert model_for_role("worker") == "@cf/meta/llama-3.3-70b-instruct-fp8-fast"  # general
    assert model_for_role("reader") == "@cf/meta/llama-3.1-8b-instruct-fast"       # fast
    assert model_for_role("bogus") == DEFAULT_MODEL                          # fallback


def test_worker_role_model_is_tool_capable():
    # the Worker executes tools, so its model MUST support tool-calling
    from unitytools.core.model_router import model_for_role
    worker = model_for_role("worker")
    spec = next(s for s in MODEL_CATALOG.values() if s["model"] == worker)
    assert spec["tools"] is True


def test_dual_agent_clone_assigns_role_models_on_cloudflare():
    from unitytools.core.config import Config
    from unitytools.core.dual_agent import DualAgentOrchestrator
    c = Config()
    c.provider = "cloudflare"
    clone = DualAgentOrchestrator._clone_config
    for role, expected in [("master", "@cf/openai/gpt-oss-120b"),
                           ("worker", "@cf/meta/llama-3.3-70b-instruct-fp8-fast"),
                           ("reader", "@cf/meta/llama-3.1-8b-instruct-fast")]:
        cc = clone(c, "qwen2.5:14b-instruct", role=role)
        assert cc.cloudflare_model == expected
        assert cc.cloudflare_auto_route is False      # the role model is authoritative
        assert cc.ollama_model == "qwen2.5:14b-instruct"   # ollama still set too


def test_dual_agent_clone_leaves_cloudflare_alone_without_a_role_or_provider():
    from unitytools.core.config import Config
    from unitytools.core.dual_agent import DualAgentOrchestrator
    clone = DualAgentOrchestrator._clone_config
    # no role -> cloudflare untouched
    c = Config(); c.provider = "cloudflare"; c.cloudflare_model = "@cf/keep/me"
    assert clone(c, "m").cloudflare_model == "@cf/keep/me"
    # role but provider is ollama -> cloudflare untouched
    c2 = Config(); c2.provider = "ollama"; c2.cloudflare_model = "@cf/keep/me"
    assert clone(c2, "m", role="master").cloudflare_model == "@cf/keep/me"


def test_orchestrator_respects_auto_route_off():
    o = _orch()
    o.config.cloudflare_auto_route = False
    o.config.cloudflare_model = "@cf/openai/gpt-oss-120b"
    o._select_ollama_tools = lambda msg: []
    captured = {}
    o._cloudflare_chat = lambda messages, tools, model=None: (
        captured.__setitem__("model", model), {"message": {"content": "ok", "tool_calls": []}})[1]
    o.chat("bana bir hikaye yaz", max_iterations=1)
    assert captured["model"] == "@cf/openai/gpt-oss-120b"   # not routed to creative
