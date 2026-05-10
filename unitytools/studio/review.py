"""Daily review runner — drives the Producer through a standup or retro
and persists its output to studio/reviews/<date>.md.

A review file accumulates across the day: morning entry first, evening
entry appended below. The same file is reused whenever the Producer
runs again on the same day; the loop runner uses this so a single day's
work has a single canonical writeup.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, Optional

from .roles import PRODUCER, RoleConfig
from .runner import RoleRunResult, RoleRunner
from .state import StudioState


Phase = Literal["morning", "evening", "adhoc"]


_BRIEFS: dict[str, str] = {
    "morning": (
        "Morning standup. Read the project summary, recent commits "
        "(last 24h), recent QA regressions (last 24h), and the current "
        "sprint. Decide today's priorities. Open up to 5 new tasks "
        "owned by the right roles. End with three lines: what changed, "
        "what's planned, what's the biggest blocker."
    ),
    "evening": (
        "Evening retro. Read the project summary, recent commits, and "
        "recent QA regressions. Summarise what got done, what regressed, "
        "and which proposed decisions still need a Critic review. If "
        "today's plan no longer matches reality, rewrite "
        "studio/sprint_current.md. End with three lines: what shipped, "
        "what slipped, what to attack first tomorrow."
    ),
    "adhoc": (
        "Ad-hoc check. Read the project summary plus recent regressions "
        "and decide if anything urgent needs a task right now. Open at "
        "most 2 tasks. End with two lines: what looks healthy, what "
        "needs immediate attention."
    ),
}


def brief_for(phase: Phase) -> str:
    return _BRIEFS.get(phase, _BRIEFS["adhoc"])


@dataclass
class ReviewRecord:
    """What was written to disk for one Producer pass."""

    phase: Phase
    path: str
    timestamp: float
    iterations: int
    tool_calls: int
    text: str


def _today_iso(now: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%d", time.localtime(now if now is not None else time.time()))


def _format_section(phase: Phase, result: RoleRunResult, now: float) -> str:
    header_label = {
        "morning": "Morning standup",
        "evening": "Evening retro",
        "adhoc": "Ad-hoc check",
    }.get(phase, "Review")
    timestamp = time.strftime("%H:%M", time.localtime(now))
    lines: list[str] = []
    lines.append(f"## {header_label} ({timestamp})")
    lines.append("")
    lines.append(result.text.strip() or "_No text returned by Producer._")
    lines.append("")
    if result.tool_calls:
        lines.append(
            f"_Tools called: {len(result.tool_calls)} — {', '.join(tc.name for tc in result.tool_calls)}_"
        )
        lines.append("")
    lines.append(
        f"_Stop reason: {result.stop_reason}, iterations: {result.iterations}._"
    )
    return "\n".join(lines) + "\n"


def write_review(state: StudioState, phase: Phase, result: RoleRunResult, now: Optional[float] = None) -> ReviewRecord:
    """Append a Producer pass to today's review file. Returns the on-disk record."""
    now = now if now is not None else time.time()
    date = _today_iso(now)
    state.paths.reviews.mkdir(parents=True, exist_ok=True)
    path = state.paths.daily_review(date)

    section = _format_section(phase, result, now)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if not existing.endswith("\n"):
            existing += "\n"
        new_content = existing + "\n" + section
    else:
        new_content = f"# {date}\n\n" + section

    state.write_doc(path, new_content)
    return ReviewRecord(
        phase=phase,
        path=str(path),
        timestamp=now,
        iterations=result.iterations,
        tool_calls=len(result.tool_calls),
        text=result.text,
    )


def run_review(
    state: StudioState,
    runner: RoleRunner,
    phase: Phase,
    role: RoleConfig = PRODUCER,
    extra_brief: str = "",
    now: Optional[float] = None,
) -> tuple[RoleRunResult, ReviewRecord]:
    """Run the Producer (or any review-capable role) and persist the output."""
    brief = brief_for(phase)
    if extra_brief:
        brief = brief + "\n\nAdditional context: " + extra_brief.strip()
    result = runner.run(role, brief)
    record = write_review(state, phase, result, now=now)
    return result, record
