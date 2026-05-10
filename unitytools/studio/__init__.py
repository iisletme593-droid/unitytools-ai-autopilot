"""Agent Game Developer Studio — long-lived project state + role agents.

Phase 1: file layout, dataclasses, atomic state I/O.
Phase 2: doc-level studio tools, three role configs (Producer / Designer
/ Critic), and a RoleRunner that drives one role through a brief.
Phase 3: vision grounding — Unity screenshot capture, Claude vision
diff against reference images, two new roles (Level Designer, Art
Director).

Importing this package registers the studio_* tools with the global
tool registry as a side effect.
"""
from .paths import StudioPaths
from .models import Task, Decision, Milestone, TaskStatus, DecisionStatus, MilestoneStatus
from .state import StudioState
from . import tools as _studio_tools  # registers @tool functions
from .tools import (
    init_studio_tools,
    init_studio_unity,
    init_studio_vision,
    ALL_STUDIO_TOOL_NAMES,
)
from .roles import (
    RoleConfig,
    PRODUCER,
    DESIGNER,
    CRITIC,
    LEVEL_DESIGNER,
    ART_DIRECTOR,
    WORKER,
    get_role,
    all_roles,
)
from .runner import (
    RoleRunner,
    RoleRunResult,
    ToolCallRecord,
    LLMClient,
    AnthropicClient,
    RehearsalLLM,
    has_rehearsal_for,
    make_default_client,
)
from .vision import VisionClient, AnthropicVisionClient, make_default_vision_client
from .config import StudioThresholds, STUDIO_DEFAULTS
from .review import Phase, ReviewRecord, brief_for, run_review, write_review
from .loop import LoopRunner, LoopStats
from .dispatch import Dispatcher, DispatchResult, DispatchSummary, DISPATCH_MAP

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
    "init_studio_unity",
    "init_studio_vision",
    "ALL_STUDIO_TOOL_NAMES",
    # roles
    "RoleConfig",
    "PRODUCER",
    "DESIGNER",
    "CRITIC",
    "LEVEL_DESIGNER",
    "ART_DIRECTOR",
    "WORKER",
    "get_role",
    "all_roles",
    # runner
    "RoleRunner",
    "RoleRunResult",
    "ToolCallRecord",
    "LLMClient",
    "AnthropicClient",
    "RehearsalLLM",
    "has_rehearsal_for",
    "make_default_client",
    # config
    "StudioThresholds",
    "STUDIO_DEFAULTS",
    # vision
    "VisionClient",
    "AnthropicVisionClient",
    "make_default_vision_client",
    # review + loop
    "Phase",
    "ReviewRecord",
    "brief_for",
    "run_review",
    "write_review",
    "LoopRunner",
    "LoopStats",
    # dispatch
    "Dispatcher",
    "DispatchResult",
    "DispatchSummary",
    "DISPATCH_MAP",
]
