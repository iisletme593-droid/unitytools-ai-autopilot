"""Studio domain models: Task, Decision, Milestone.

These are stored on disk as JSON (backlog, milestones) or JSONL (decisions —
append-only history). Each model has explicit to_dict / from_dict so the
on-disk schema is decoupled from runtime field reordering.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    REVIEW = "review"
    DONE = "done"
    REJECTED = "rejected"


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class MilestoneStatus(str, Enum):
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    ABANDONED = "abandoned"


# Roles that can own tasks. Each one has a dispatcher route in
# studio/dispatch.py (DISPATCH_MAP). Extend this list whenever a new
# RoleConfig is added in studio/roles.py — studio_add_task validates
# the role field against this tuple.
ROLES = (
    # Phase 2 originals
    "producer",
    "designer",
    "art_director",
    "level_designer",
    "tech_artist",
    "qa",
    "critic",
    # Phase 4+ executors
    "worker",
    # Phase 23-30 specialists
    "playtester",
    "physics_qa",
    "audio_director",
    "audio_engineer",
    "lighting_director",
    "camera_director",
    "vfx_director",
    # Phase 31-41 specialists
    "ui_builder",
    "build_engineer",
    "atmosphere_director",
    "material_artist",
    "marketing_director",
    "game_balancer",
    "localization_lead",
    "tutorial_designer",
)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> float:
    return time.time()


@dataclass
class Task:
    title: str
    role: str = "producer"
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    id: str = field(default_factory=_new_id)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    milestone: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        kwargs = dict(data)
        status = kwargs.get("status", TaskStatus.PENDING.value)
        kwargs["status"] = TaskStatus(status) if isinstance(status, str) else status
        return cls(**kwargs)

    def touch(self) -> None:
        self.updated_at = _now()


@dataclass
class Decision:
    title: str
    summary: str
    rationale: str = ""
    author_role: str = "producer"
    status: DecisionStatus = DecisionStatus.PROPOSED
    id: str = field(default_factory=_new_id)
    timestamp: float = field(default_factory=_now)
    alternatives_considered: list[str] = field(default_factory=list)
    superseded_by: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Decision":
        kwargs = dict(data)
        status = kwargs.get("status", DecisionStatus.PROPOSED.value)
        kwargs["status"] = DecisionStatus(status) if isinstance(status, str) else status
        return cls(**kwargs)


@dataclass
class Milestone:
    name: str
    description: str = ""
    status: MilestoneStatus = MilestoneStatus.PLANNING
    id: str = field(default_factory=_new_id)
    target_date: Optional[str] = None  # ISO date YYYY-MM-DD
    success_criteria: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Milestone":
        kwargs = dict(data)
        status = kwargs.get("status", MilestoneStatus.PLANNING.value)
        kwargs["status"] = MilestoneStatus(status) if isinstance(status, str) else status
        return cls(**kwargs)
