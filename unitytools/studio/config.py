"""Tunable thresholds and limits for studio role behaviour.

Until Phase 6 these were magic numbers buried in role prompts ("below 0.5",
"below 0.6") and CLI defaults (max iterations, max tasks per producer
run). Centralising them here means a single edit changes both the prompt
the LLM sees and the code paths that read them.

Phase 6 ships a single global default (`STUDIO_DEFAULTS`). A future
phase can let projects override these via studio/config.json without
changing module imports.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StudioThresholds:
    """All tunable studio numbers in one frozen object."""

    # Worker decides "blocked" when reference-vs-screenshot composition_match
    # drops below this value. Below this, the change made things worse.
    worker_block_threshold: float = 0.5

    # Level Designer files a "re-block level" decision when composition_match
    # drops below this. Higher than the Worker threshold so a critic gets a
    # chance to weigh in before a costly redo.
    level_designer_reblock_threshold: float = 0.6

    # Hard caps on tool-call rounds per role run. Workers get more headroom
    # than reviewers because they take more steps (snapshot + place +
    # verify + status update is at least 4 calls, plus reads and retries).
    max_role_iterations: int = 8
    max_worker_iterations: int = 12

    # Producer should not flood the backlog. Five tasks fit comfortably
    # in a half-day of focused work.
    max_tasks_per_producer_run: int = 5


STUDIO_DEFAULTS = StudioThresholds()
