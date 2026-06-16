"""Cloudflare Workers AI model router -- pick the best model per task.

A CODE-DERIVED catalog of task-specialised Cloudflare Workers AI models plus a
deterministic router that reads a chat message, detects the task type, and selects
the most suitable model. It is controllable from chat (an explicit "X modeliyle" /
"use the coder model" override) and otherwise auto-detects. Pure + deterministic
(no network, no RNG); the orchestrator calls ``select_model()`` once per turn.

Every model id here was verified against developers.cloudflare.com. The two flags:
  * ``tools`` -- the model supports function/tool calling on /ai/run (safe for the
    Unity tool-loop);
  * ``chat``  -- it accepts the chat ``messages`` array on /ai/run.

LIVE routing only ever picks among the TEXT-CHAT models (reasoning / general /
coding / creative / fast), because the orchestrator's loop sends chat messages and
expects text + tool_calls back. ``vision`` (needs image input) and ``image`` (returns
binary, no messages) are catalogued for the report and future dedicated tools, but
``select_model`` does not route the text loop to them -- doing so would break it.
"""
from __future__ import annotations

import re
from typing import Any, Optional

# task_type -> spec. Model ids verified on developers.cloudflare.com.
MODEL_CATALOG: dict[str, dict[str, Any]] = {
    "reasoning": {
        "model": "@cf/openai/gpt-oss-120b",
        "tools": True, "chat": True, "modality": "text", "live": True,
        "strengths": "high reasoning, agentic, planning -- the safe tool-capable default",
        "kw_en": ("reason", "think", "step by step", "logic", "prove", "analyze", "why"),
        "kw_tr": ("dusun", "mantik", "adim adim", "ispatla", "analiz", "akil yurut", "neden"),
    },
    "general": {
        "model": "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        "tools": True, "chat": True, "modality": "text", "live": True,
        "strengths": "strong all-round instruct + reliable tool-calling, fast (fp8)",
        "kw_en": ("help", "answer", "explain", "chat", "general", "assist", "tell me"),
        "kw_tr": ("yardim", "cevap", "acikla", "sohbet", "genel", "anlat"),
    },
    "coding": {
        "model": "@cf/qwen/qwen2.5-coder-32b-instruct",
        "tools": False, "chat": True, "modality": "text", "live": True,
        "strengths": "SOTA open-source coder (text-only completion)",
        "kw_en": ("code", "function", "bug", "debug", "refactor", "program", "regex", "compile", "stacktrace"),
        "kw_tr": ("kod", "fonksiyon", "ayikla", "refactor", "derle", "betik", "hata ayikla"),
    },
    "creative": {
        "model": "@cf/zai-org/glm-4.7-flash",
        "tools": True, "chat": True, "modality": "text", "live": True,
        "strengths": "dialogue / storytelling, multilingual creative writing",
        "kw_en": ("story", "poem", "dialogue", "creative", "narrative", "character", "lyrics", "screenplay"),
        "kw_tr": ("hikaye", "siir", "diyalog", "yaratici", "anlati", "karakter", "senaryo", "masal"),
    },
    "fast": {
        "model": "@cf/meta/llama-3.1-8b-instruct-fast",
        "tools": False, "chat": True, "modality": "text", "live": True,
        "strengths": "latency-optimised 8B for simple / cheap / high-throughput tasks",
        "kw_en": ("quick", "fast", "simple", "short", "classify", "extract", "summarize", "summarise", "tldr"),
        "kw_tr": ("hizli", "cabuk", "basit", "kisa", "siniflandir", "cikar", "ozetle", "ozet"),
    },
    # --- catalogued but NOT routed by the text chat loop (see module docstring) ---
    "vision": {
        "model": "@cf/meta/llama-3.2-11b-vision-instruct",
        "tools": True, "chat": True, "modality": "text+vision", "live": False,
        "strengths": "image reasoning, captioning, visual Q&A (needs an image input)",
        "kw_en": ("caption", "vqa", "describe image", "what is in this image"),
        "kw_tr": ("altyazi", "resmi anlat", "goruntu analiz", "resimde ne var"),
    },
    "image": {
        "model": "@cf/black-forest-labs/flux-1-schnell",
        "tools": False, "chat": False, "modality": "image-generation", "live": False,
        "strengths": "fast high-quality text-to-image (returns base64, not chat)",
        "kw_en": ("generate image", "draw", "text to image", "render an image", "create a picture", "illustration"),
        "kw_tr": ("gorsel olustur", "ciz", "metinden resim", "resim uret", "illustrasyon", "tasarla"),
    },
}

# The text-chat tasks the live router may choose, in detection priority order
# (most distinctive first; "general" is the catch-all default).
_LIVE_TASKS = ("coding", "creative", "reasoning", "fast", "general")
DEFAULT_TASK = "reasoning"                         # gpt-oss-120b: tool-capable, agentic
DEFAULT_MODEL = MODEL_CATALOG[DEFAULT_TASK]["model"]

# short words the user can name in chat to FORCE a task/model
_ALIAS_TO_TASK = {
    "reasoning": "reasoning", "reason": "reasoning", "akil": "reasoning", "mantik": "reasoning",
    "gpt-oss": "reasoning", "gptoss": "reasoning", "gpt": "reasoning",
    "general": "general", "genel": "general", "llama": "general",
    "coder": "coding", "coding": "coding", "kod": "coding", "kodlama": "coding", "qwen": "coding",
    "creative": "creative", "yaratici": "creative", "hikaye": "creative", "glm": "creative",
    "fast": "fast", "hizli": "fast",
    "vision": "vision", "gorsel": "vision",
    "image": "image", "resim": "image", "flux": "image",
}

_TR_FOLD = str.maketrans({"ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
                          "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u"})


def _norm(text: Optional[str]) -> str:
    return (text or "").translate(_TR_FOLD).lower()


def _matches(norm_text: str, keywords: tuple[str, ...]) -> bool:
    """Multi-word keywords match as a substring; single words match a whole token
    (so "kod" hits "kodla" but not a stray substring inside an unrelated word)."""
    tokens = re.findall(r"[a-z0-9]+", norm_text)
    for kw in keywords:
        k = _norm(kw)
        if " " in k:
            if k in norm_text:
                return True
        elif any(tok == k or tok.startswith(k) for tok in tokens):
            return True
    return False


def detect_task_type(text: str) -> str:
    """Detect the live text-chat task type from a message (deterministic). Returns one
    of the _LIVE_TASKS; defaults to 'general' when nothing distinctive matches."""
    norm = _norm(text)
    for task in _LIVE_TASKS:
        spec = MODEL_CATALOG[task]
        if task == "general":
            continue                                # general is the fallback, checked last
        if _matches(norm, spec["kw_en"]) or _matches(norm, spec["kw_tr"]):
            return task
    return "general"


def parse_model_override(text: str) -> Optional[str]:
    """Pull an explicit model/task choice out of the message, or None. Fires only on a
    clear cue: an alias next to the word "model" ("coder modeliyle", "use the fast
    model", "model: creative"), or a raw "@cf/..." id mapped back to its task."""
    norm = _norm(text)
    # a raw catalog id named directly
    for task, spec in MODEL_CATALOG.items():
        if spec["model"].lower() in norm:
            return task
    # an alias adjacent to the word "model"
    for m in re.finditer(r"([a-z0-9\-]+)\s*model|model\s*[:=]?\s*([a-z0-9\-]+)", norm):
        alias = m.group(1) or m.group(2)
        if alias in _ALIAS_TO_TASK:
            return _ALIAS_TO_TASK[alias]
    return None


def select_model(text: str, needs_tools: bool = False, config: Any = None) -> dict[str, Any]:
    """Pick the Cloudflare model for this turn. Returns {model, task, reason, routed}.

    Order: (1) an explicit chat override wins; (2) if auto-routing is off, the
    configured model is used; (3) a tool-requiring turn always gets a verified
    tool-capable model (so the Unity tool-loop never breaks); (4) otherwise the task
    type is auto-detected among the text-chat models. When ``needs_tools`` is set, a
    non-tool override/task is upgraded to the tool-capable default rather than break.
    """
    configured = (getattr(config, "cloudflare_model", "") or DEFAULT_MODEL)
    auto = getattr(config, "cloudflare_auto_route", True) if config is not None else True

    forced = parse_model_override(text)
    if forced:
        spec = MODEL_CATALOG[forced]
        if not spec.get("live", False) or (needs_tools and not spec["tools"]):
            # honour the intent but keep the loop working with a tool-capable model
            return {"model": DEFAULT_MODEL, "task": "reasoning", "routed": True,
                    "reason": f"override '{forced}' not usable here (live/tools); kept the tool-capable default"}
        return {"model": spec["model"], "task": forced, "routed": True,
                "reason": f"explicit override -> {forced}"}

    if not auto:
        return {"model": configured, "task": "config", "routed": False,
                "reason": "auto-routing off; using the configured model"}

    if needs_tools:
        return {"model": MODEL_CATALOG["reasoning"]["model"], "task": "reasoning", "routed": True,
                "reason": "tool-calling turn -> verified tool-capable reasoning model"}

    task = detect_task_type(text)
    return {"model": MODEL_CATALOG[task]["model"], "task": task, "routed": True,
            "reason": f"auto-detected '{task}' from the message"}


# dual-agent role -> task. Each agent gets the model that fits its job: the Master
# plans (reasoning), the Worker executes tools (a tool-capable general model), the
# Reader does fast context interpretation (a cheap fast model).
_ROLE_TO_TASK = {"master": "reasoning", "worker": "general", "reader": "fast"}


def model_for_role(role: str) -> str:
    """The Cloudflare model best suited to a dual-agent role (master/worker/reader).
    Unknown roles fall back to the default. The Worker's model is always tool-capable."""
    task = _ROLE_TO_TASK.get((role or "").strip().lower(), DEFAULT_TASK)
    return MODEL_CATALOG[task]["model"]


def list_models(live_only: bool = False) -> list[dict[str, Any]]:
    """The catalog as a flat list (for tools/reports). live_only drops vision/image."""
    out = []
    for task, spec in MODEL_CATALOG.items():
        if live_only and not spec.get("live", False):
            continue
        out.append({"task": task, "model": spec["model"], "tools": spec["tools"],
                    "chat": spec["chat"], "modality": spec["modality"],
                    "live": spec.get("live", False), "strengths": spec["strengths"]})
    return out


def build_model_router_report() -> str:
    """A code-derived, user-facing report of the model catalog + routing (markdown,
    pure ASCII). Reads MODEL_CATALOG so it can never drift."""
    lines = ["# Cloudflare Model Router", ""]
    lines.append("The studio picks a task-specialised Cloudflare Workers AI model per turn. "
                 "Tool-calling (Unity action) turns always use a verified tool-capable model; "
                 "plain chat is routed by task. Override from chat with e.g. 'coder modeliyle' "
                 "or 'use the creative model'. This report is generated from the live catalog.")
    lines.append("")
    lines.append(f"## Live text routing (default task: {DEFAULT_TASK} -> {DEFAULT_MODEL})")
    for task in _LIVE_TASKS:
        spec = MODEL_CATALOG[task]
        tools = "tools" if spec["tools"] else "no-tools"
        lines.append(f"- **{task}** -> `{spec['model']}` ({tools}) -- {spec['strengths']}")
    lines.append("")
    lines.append("## Catalogued for dedicated use (not routed by the text loop)")
    for task in ("vision", "image"):
        spec = MODEL_CATALOG[task]
        lines.append(f"- **{task}** -> `{spec['model']}` ({spec['modality']}) -- {spec['strengths']}")
    lines.append("")
    lines.append("Set CLOUDFLARE_AUTO_ROUTE=0 to disable auto-routing and always use CLOUDFLARE_MODEL.")
    return "\n".join(lines)
