"""Task durumu izleme. UI'lara progress göstermek için."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Task:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    status: TaskStatus = TaskStatus.PENDING
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0  # 0.0 - 1.0
    log_lines: list[str] = field(default_factory=list)

    def start(self) -> None:
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()

    def finish_success(self, result: Any = None) -> None:
        self.status = TaskStatus.SUCCESS
        self.finished_at = time.time()
        self.result = result
        self.progress = 1.0

    def finish_error(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.finished_at = time.time()
        self.error = error

    @property
    def duration(self) -> Optional[float]:
        if self.started_at is None:
            return None
        end = self.finished_at or time.time()
        return end - self.started_at


class TaskQueue:
    """In-memory task tracker. Kalıcılık şart değil — yeniden başladığında temiz başla."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._listeners: list[Callable[[Task], None]] = []

    def add(self, name: str) -> Task:
        task = Task(name=name)
        self._tasks[task.id] = task
        self._notify(task)
        return task

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def all(self) -> list[Task]:
        return list(self._tasks.values())

    def update(self, task: Task) -> None:
        self._tasks[task.id] = task
        self._notify(task)

    def subscribe(self, listener: Callable[[Task], None]) -> None:
        self._listeners.append(listener)

    def _notify(self, task: Task) -> None:
        for listener in self._listeners:
            try:
                listener(task)
            except Exception:
                pass  # listener patladıysa diğerlerini engellemesin
