"""Tunable thresholds and limits for studio role behaviour.

Until Phase 6 these were magic numbers buried in role prompts ("below 0.5",
"below 0.6") and CLI defaults (max iterations, max tasks per producer
run). Centralising them here means a single edit changes both the prompt
the LLM sees and the code paths that read them.

Phase 6 shipped a single global default (`STUDIO_DEFAULTS`).
Phase 10a adds `load_thresholds(paths)` which merges optional
`studio/config.json` overrides on top of the defaults — projects can
tune iteration caps and task limits without forking the source.

Note on prompt thresholds (worker_block_threshold,
level_designer_reblock_threshold): these are templated into role
prompts at module-import time. Project overrides apply to code paths
but DO NOT rewrite the prompts themselves; for that, edit config.py
defaults and reimport, or write a wrapper that builds custom
RoleConfigs. Code-side caps (max_*) are fully overridable.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, fields, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .paths import StudioPaths

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StudioThresholds:
    """All tunable studio numbers in one frozen object."""

    # Worker decides "blocked" when reference-vs-screenshot composition_match
    # drops below this value. Below this, the change made things worse.
    # NOTE: also templated into the Worker's system prompt at import time.
    worker_block_threshold: float = 0.5

    # Level Designer files a "re-block level" decision when composition_match
    # drops below this. Higher than the Worker threshold so a critic gets a
    # chance to weigh in before a costly redo.
    # NOTE: also templated into the Level Designer prompt at import time.
    level_designer_reblock_threshold: float = 0.6

    # Hard caps on tool-call rounds per role run. Workers get more headroom
    # than reviewers because they take more steps (snapshot + place +
    # verify + status update is at least 4 calls, plus reads and retries).
    max_role_iterations: int = 8
    max_worker_iterations: int = 12

    # Producer should not flood the backlog. Five tasks fit comfortably
    # in a half-day of focused work.
    max_tasks_per_producer_run: int = 5

    # Phase 24: per-scene performance budgets. The Physics QA role
    # checks the live scene against these; any metric over budget
    # becomes a "violation" the role files as a decision + follow-up
    # task. Defaults track Unity's own "too many" suggestion thresholds
    # from ProfileScenePerformance.cs.
    perf_triangle_budget: int = 1_000_000
    perf_renderer_budget: int = 1_000
    perf_shadow_caster_budget: int = 200
    perf_unique_material_budget: int = 250
    perf_shadow_light_budget: int = 2


STUDIO_DEFAULTS = StudioThresholds()


def load_thresholds(paths: "StudioPaths") -> StudioThresholds:
    """Read studio/config.json and return defaults merged with overrides.

    Returns STUDIO_DEFAULTS unchanged when:
    - the file does not exist
    - the file is malformed JSON (logs a warning)
    - the file is not a JSON object (logs a warning)

    Otherwise returns `replace(STUDIO_DEFAULTS, **valid_overrides)`.
    Unknown keys are ignored with a single warning per call so a typo
    in a project's config.json doesn't silently disable a tuning.
    """
    config_file = paths.root / "config.json"
    if not config_file.exists():
        return STUDIO_DEFAULTS
    try:
        raw = config_file.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("studio/config.json could not be read: %s", exc)
        return STUDIO_DEFAULTS
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("studio/config.json is malformed JSON (%s); using defaults.", exc)
        return STUDIO_DEFAULTS
    if not isinstance(data, dict):
        logger.warning("studio/config.json must be a JSON object; using defaults.")
        return STUDIO_DEFAULTS

    valid_fields = {f.name for f in fields(StudioThresholds)}
    overrides: dict = {}
    unknown: list[str] = []
    for key, value in data.items():
        if key in valid_fields:
            overrides[key] = value
        else:
            unknown.append(key)
    if unknown:
        logger.warning(
            "studio/config.json: ignored unknown keys %s. Valid keys: %s",
            sorted(unknown),
            sorted(valid_fields),
        )
    if not overrides:
        return STUDIO_DEFAULTS
    try:
        return replace(STUDIO_DEFAULTS, **overrides)
    except TypeError as exc:
        # replace() complains if a value's type can't bind (e.g. a list where
        # a float was expected). Bail back to defaults rather than crashing.
        logger.warning(
            "studio/config.json: type mismatch (%s); using defaults.", exc
        )
        return STUDIO_DEFAULTS
