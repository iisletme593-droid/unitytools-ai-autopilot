"""Studio state I/O — read, write, append.

All disk writes go through atomic helpers so a crash mid-write cannot
leave half-written JSON. Decisions are append-only (history); backlog
and milestones are full-rewrites (small enough that this is fine).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, Iterator

from .models import Decision, Milestone, Task
from .paths import StudioPaths


def _atomic_write_text(path: Path, content: str) -> None:
    """Write content to path atomically: temp file in same dir, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data) -> None:
    _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


class StudioState:
    """High-level read/write API over a StudioPaths layout."""

    def __init__(self, paths: StudioPaths):
        self.paths = paths

    @property
    def thresholds(self):
        """Lazy-load tunables from studio/config.json (defaults if absent).

        Re-read on every access so a project can tune limits between two
        consecutive role runs without reimporting the package.
        """
        from .config import load_thresholds

        return load_thresholds(self.paths)

    # ── Tasks (backlog.json) ────────────────────────────────────────────
    def load_tasks(self) -> list[Task]:
        data = _read_json(self.paths.backlog, {"tasks": []})
        return [Task.from_dict(item) for item in data.get("tasks", [])]

    def save_tasks(self, tasks: Iterable[Task]) -> None:
        _write_json(self.paths.backlog, {"tasks": [t.to_dict() for t in tasks]})

    def add_task(self, task: Task) -> Task:
        tasks = self.load_tasks()
        tasks.append(task)
        self.save_tasks(tasks)
        return task

    def update_task(self, task: Task) -> None:
        tasks = self.load_tasks()
        task.touch()
        for i, existing in enumerate(tasks):
            if existing.id == task.id:
                tasks[i] = task
                self.save_tasks(tasks)
                return
        raise KeyError(f"Task not found: {task.id}")

    # ── Decisions (decisions.jsonl, append-only) ────────────────────────
    def append_decision(self, decision: Decision) -> Decision:
        path = self.paths.decisions
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(decision.to_dict(), ensure_ascii=False) + "\n"
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(line)
        return decision

    def iter_decisions(self) -> Iterator[Decision]:
        path = self.paths.decisions
        if not path.exists():
            return iter(())

        def _gen() -> Iterator[Decision]:
            with path.open("r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    yield Decision.from_dict(json.loads(raw))

        return _gen()

    def load_decisions(self) -> list[Decision]:
        return list(self.iter_decisions())

    # ── Milestones (milestones.json) ────────────────────────────────────
    def load_milestones(self) -> list[Milestone]:
        data = _read_json(self.paths.milestones, {"milestones": []})
        return [Milestone.from_dict(item) for item in data.get("milestones", [])]

    def save_milestones(self, milestones: Iterable[Milestone]) -> None:
        _write_json(self.paths.milestones, {"milestones": [m.to_dict() for m in milestones]})

    def add_milestone(self, milestone: Milestone) -> Milestone:
        milestones = self.load_milestones()
        milestones.append(milestone)
        self.save_milestones(milestones)
        return milestone

    # ── QA regression log (qa/regression.jsonl, append-only) ────────────
    def append_regression_entry(self, entry: dict) -> None:
        path = self.paths.qa_regression
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ── Free-form documents (gdd.md, art_bible.md, sprint_current.md) ───
    def read_doc(self, path: Path) -> str:
        return path.read_text(encoding="utf-8") if path.exists() else ""

    def write_doc(self, path: Path, content: str) -> None:
        if not content.endswith("\n"):
            content = content + "\n"
        _atomic_write_text(path, content)

    # ── Summary ─────────────────────────────────────────────────────────
    def summary(self) -> dict:
        """Counts + status snapshot for `studio status`."""
        tasks = self.load_tasks()
        milestones = self.load_milestones()
        by_status: dict[str, int] = {}
        by_role: dict[str, int] = {}
        for t in tasks:
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            by_role[t.role] = by_role.get(t.role, 0) + 1
        decisions_count = sum(1 for _ in self.iter_decisions())
        return {
            "studio_root": str(self.paths.root),
            "exists": self.paths.exists(),
            "task_count": len(tasks),
            "tasks_by_status": by_status,
            "tasks_by_role": by_role,
            "milestone_count": len(milestones),
            "decision_count": decisions_count,
            "has_gdd": self.paths.gdd.exists(),
            "has_art_bible": self.paths.art_bible.exists(),
            "has_sprint": self.paths.sprint_current.exists(),
        }
