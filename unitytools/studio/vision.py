"""Vision client — compare a reference image to a screenshot, return JSON diff.

The studio's `studio_compare_to_reference` tool calls a VisionClient. In
production that's AnthropicVisionClient (Claude Sonnet/Opus with vision).
In tests we inject a deterministic fake.

Output schema (the vision model is asked to fill exactly this shape):

    {
      "composition_match": 0.0..1.0,
      "palette_match": 0.0..1.0,
      "missing":   ["objects in reference that are not in the screenshot"],
      "extra":     ["objects in screenshot that are not in the reference"],
      "misplaced": [{"item": str, "where_now": str, "where_should_be": str}],
      "notes":     "short summary"
    }
"""
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Optional, Protocol

from ..core.config import Config

logger = logging.getLogger(__name__)


DEFAULT_INSTRUCTION = """You are comparing a target reference image (first
image) to the current scene screenshot (second image).

Reply with ONE JSON object and NOTHING ELSE. Use exactly these keys:
  composition_match (number, 0..1) — how close the overall composition is
  palette_match     (number, 0..1) — how close the color palette is
  missing  (array of strings) — items in the reference that are missing in the screenshot
  extra    (array of strings) — items in the screenshot that are not in the reference
  misplaced (array of objects with keys item, where_now, where_should_be)
  notes    (string) — one-sentence summary of the most important issue

Be concrete. Do not include markdown fences."""


_IMAGE_MIME_BY_SUFFIX = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def guess_mime(path: Path) -> str:
    return _IMAGE_MIME_BY_SUFFIX.get(path.suffix.lower(), "image/png")


def _extract_json_object(text: str) -> dict[str, Any]:
    """Pull the first {...} block out of the model's reply.

    Models occasionally wrap the JSON in fences or chat. We strip both.
    """
    text = text.strip()
    if text.startswith("```"):
        # ```json\n{...}\n```
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    # First {...} match — naive but works because we asked for a single object.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in vision reply: {text[:200]!r}")
    return json.loads(match.group(0))


class VisionClient(Protocol):
    """Single method: compare two images and return the parsed diff dict.

    Implementations decide how to call the underlying model.
    """

    def compare(self, reference_bytes: bytes, reference_mime: str, candidate_bytes: bytes, candidate_mime: str, instruction: str = "") -> dict:  # noqa: E501
        ...


class AnthropicVisionClient:
    """Production VisionClient. Sends both images in one user turn to Claude."""

    def __init__(self, config: Config, model: Optional[str] = None, max_tokens: int = 2048):
        from anthropic import Anthropic  # lazy

        if not config.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; cannot use AnthropicVisionClient.")
        self._client = Anthropic(api_key=config.api_key)
        self._model = model or config.model
        self._max_tokens = max_tokens

    def compare(
        self,
        reference_bytes: bytes,
        reference_mime: str,
        candidate_bytes: bytes,
        candidate_mime: str,
        instruction: str = "",
    ) -> dict:
        instruction = (instruction or DEFAULT_INSTRUCTION).strip()
        ref_b64 = base64.standard_b64encode(reference_bytes).decode("ascii")
        cand_b64 = base64.standard_b64encode(candidate_bytes).decode("ascii")
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Reference image (target):"},
                        {"type": "image", "source": {"type": "base64", "media_type": reference_mime, "data": ref_b64}},
                        {"type": "text", "text": "Current screenshot (candidate):"},
                        {"type": "image", "source": {"type": "base64", "media_type": candidate_mime, "data": cand_b64}},
                        {"type": "text", "text": instruction},
                    ],
                }
            ],
        )
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += block.text
        try:
            return _extract_json_object(text)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("Vision reply did not parse as JSON: %s", exc)
            return {
                "composition_match": None,
                "palette_match": None,
                "missing": [],
                "extra": [],
                "misplaced": [],
                "notes": f"Vision model returned non-JSON: {text[:500]}",
            }


def make_default_vision_client(config: Config) -> VisionClient:
    """Default to Anthropic — Claude is the only vision provider supported in Phase 3.

    If no API key is set, raises so the caller can produce a clean error.
    """
    if not config.api_key:
        raise RuntimeError(
            "Vision compare requires ANTHROPIC_API_KEY (Claude vision). "
            "Set it in .env or pass a custom VisionClient."
        )
    return AnthropicVisionClient(config)
