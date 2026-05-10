"""Recurring producer loop.

Runs the Producer at fixed intervals (default daily at script start),
saving each pass to the day's review file. Designed to be cheap to test:
`run(once=True)` does exactly one iteration and returns; `run(...)` with
an interval sleeps in small chunks so Ctrl+C is responsive.

For real autonomy bind this to the user's existing scheduler (cron,
launchd, Windows Task Scheduler, or the project's MCP scheduled-tasks).
The loop here is a self-contained alternative.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from .review import Phase, ReviewRecord, run_review
from .runner import RoleRunner
from .state import StudioState

logger = logging.getLogger(__name__)


# Sleep in small slices so a Ctrl+C lands within a second instead of after
# the full interval.
_SLICE_SECONDS = 1.0


@dataclass
class LoopStats:
    iterations: int = 0
    last_phase: Optional[Phase] = None
    last_record: Optional[ReviewRecord] = None
    records: list[ReviewRecord] = field(default_factory=list)


class LoopRunner:
    """Simple time-based loop that runs the Producer review on a cadence."""

    def __init__(
        self,
        state: StudioState,
        runner: RoleRunner,
        sleep_fn: Callable[[float], None] = time.sleep,
        now_fn: Callable[[], float] = time.time,
    ):
        self.state = state
        self.runner = runner
        self._sleep = sleep_fn
        self._now = now_fn
        self.stats = LoopStats()
        self._stop_requested = False

    def request_stop(self) -> None:
        self._stop_requested = True

    def run(
        self,
        once: bool = False,
        interval_seconds: float = 86400.0,
        max_iterations: Optional[int] = None,
        phase_picker: Optional[Callable[[float], Phase]] = None,
    ) -> LoopStats:
        """Run the producer review at most max_iterations times.

        - `once=True` short-circuits to a single iteration.
        - `phase_picker(now)` returns "morning" / "evening" / "adhoc";
          default uses local clock-hour: morning if hour < 12 else evening.
        """
        picker = phase_picker or _default_phase_picker
        cap = 1 if once else (max_iterations if max_iterations is not None else None)
        i = 0
        while True:
            if self._stop_requested:
                logger.info("Loop stopped by request after %d iterations", self.stats.iterations)
                break
            now = self._now()
            phase: Phase = picker(now)
            try:
                _result, record = run_review(self.state, self.runner, phase, now=now)
                self.stats.records.append(record)
                self.stats.last_record = record
                self.stats.last_phase = phase
            except Exception:
                logger.exception("Producer review failed; continuing")
            self.stats.iterations += 1
            i += 1

            if cap is not None and i >= cap:
                break

            # Sleep in slices so Ctrl+C / request_stop is responsive.
            slept = 0.0
            while slept < interval_seconds and not self._stop_requested:
                step = min(_SLICE_SECONDS, interval_seconds - slept)
                self._sleep(step)
                slept += step

        return self.stats


def _default_phase_picker(now: float) -> Phase:
    hour = time.localtime(now).tm_hour
    if hour < 12:
        return "morning"
    return "evening"
