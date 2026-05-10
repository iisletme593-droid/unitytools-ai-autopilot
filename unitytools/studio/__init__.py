"""Agent Game Developer Studio — long-lived project state + role agents.

Phase 1: file layout, dataclasses, atomic state I/O.
Phase 2: doc-level studio tools, three role configs (Producer / Designer
/ Critic), and a RoleRunner that drives one role through a brief.
Higher-level engine roles and the producer loop build on this.

Importing this package registers the studio_* tools with the global
tool registry as a side effect.
"""
from .paths import StudioPaths
from .models import Task, Decision, Milestone, TaskStatus, DecisionStatus, MilestoneStatus
from .state import StudioState
from . import tools as _studio_tools  # registers @tool functions
from .tools import init_studio_tools, ALL_STUDIO_TOOL_NAMES
from .roles import RoleConfig, PRODUCER, DESIGNER, CRITIC, get_role, all_roles
from .runner import RoleRunner, RoleRunResult, ToolCallRecord, LLMClient, AnthropicClient, make_default_client

__all__ = [
    # state
    "StudioPaths",
    "StudioState",
    "Task",
    "Decision",
    "Milestone",
    "TaskStatus",
    "DecisionStatus",
    "MilestoneStatus",
    # tools
    "init_studio_tools",
    "ALL_STUDIO_TOOL_NAMES",
    # roles
    "RoleConfig",
    "PRODUCER",
    "DESIGNER",
    "CRITIC",
    "get_role",
    "all_roles",
    # runner
    "RoleRunner",
    "RoleRunResult",
    "ToolCallRecord",
    "LLMClient",
    "AnthropicClient",
    "make_default_client",
]
