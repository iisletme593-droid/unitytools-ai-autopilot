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
    init_studio_blender,
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
    PLAYTESTER,
    PHYSICS_QA,
    AUDIO_DIRECTOR,
    AUDIO_ENGINEER,
    LIGHTING_DIRECTOR,
    CAMERA_DIRECTOR,
    get_role,
    all_roles,
)
from .runner import (
    RoleRunner,
    RoleRunResult,
    ToolCallRecord,
    LLMClient,
    AnthropicClient,
    OllamaClient,
    RehearsalLLM,
    has_rehearsal_for,
    make_default_client,
)
from .vision import VisionClient, AnthropicVisionClient, make_default_vision_client
from .config import StudioThresholds, STUDIO_DEFAULTS, load_thresholds
from .review import Phase, ReviewRecord, brief_for, run_review, write_review
from .loop import LoopRunner, LoopStats
from .dispatch import Dispatcher, DispatchResult, DispatchSummary, DISPATCH_MAP
from .diagnostics import Check, run_diagnostics, has_failure
from .archive import (
    ArchiveResult,
    DEFAULT_AGE_DAYS,
    DEFAULT_ARCHIVABLE_STATUSES,
    archive_old_tasks,
    archive_summary,
    load_archived_tasks,
    query_archive,
)
from .decisions import (
    decisions_summary,
    find_decision,
    latest_decisions,
    query_decisions,
    ratify_decision,
)
from .milestones import all_milestones_with_progress, milestone_progress
from .export import SCHEMA_VERSION as EXPORT_SCHEMA_VERSION, build_snapshot, snapshot_to_json
from .import_snapshot import (
    ImportResult,
    SnapshotIncompatibleError,
    import_snapshot,
    load_snapshot_file,
)

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
    "init_studio_blender",
    "ALL_STUDIO_TOOL_NAMES",
    # roles
    "RoleConfig",
    "PRODUCER",
    "DESIGNER",
    "CRITIC",
    "LEVEL_DESIGNER",
    "ART_DIRECTOR",
    "WORKER",
    "PLAYTESTER",
    "PHYSICS_QA",
    "AUDIO_DIRECTOR",
    "AUDIO_ENGINEER",
    "LIGHTING_DIRECTOR",
    "CAMERA_DIRECTOR",
    "get_role",
    "all_roles",
    # runner
    "RoleRunner",
    "RoleRunResult",
    "ToolCallRecord",
    "LLMClient",
    "AnthropicClient",
    "OllamaClient",
    "RehearsalLLM",
    "has_rehearsal_for",
    "make_default_client",
    # config
    "StudioThresholds",
    "STUDIO_DEFAULTS",
    "load_thresholds",
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
    # diagnostics
    "Check",
    "run_diagnostics",
    "has_failure",
    # archive
    "ArchiveResult",
    "DEFAULT_AGE_DAYS",
    "DEFAULT_ARCHIVABLE_STATUSES",
    "archive_old_tasks",
    "archive_summary",
    "load_archived_tasks",
    "query_archive",
    "query_decisions",
    "decisions_summary",
    "latest_decisions",
    "ratify_decision",
    "find_decision",
    "milestone_progress",
    "all_milestones_with_progress",
    # export
    "EXPORT_SCHEMA_VERSION",
    "build_snapshot",
    "snapshot_to_json",
    "ImportResult",
    "SnapshotIncompatibleError",
    "import_snapshot",
    "load_snapshot_file",
]
