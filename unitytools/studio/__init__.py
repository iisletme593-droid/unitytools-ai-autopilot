"""Agent Game Developer Studio — long-lived project state.

Phase 1 surface: file layout, dataclasses, atomic state I/O.
Higher-level role agents and the producer loop build on this.
"""
from .paths import StudioPaths
from .models import Task, Decision, Milestone, TaskStatus, DecisionStatus, MilestoneStatus
from .state import StudioState

__all__ = [
    "StudioPaths",
    "StudioState",
    "Task",
    "Decision",
    "Milestone",
    "TaskStatus",
    "DecisionStatus",
    "MilestoneStatus",
]
