"""Auto-dispatch — close the studio's autonomy loop.

Until Phase 7, a Producer review opened tasks but nothing executed
them — a human had to run `studio-execute --task-id …` for each one.
The Dispatcher walks the backlog, picks the right role for each
pending task, builds a brief, runs the role, and reconciles the
final task status. Engine-aware tasks need a live Unity bridge and
optional vision client; doc-only tasks run without either.

Routing is intentionally narrow:
    role on task ──────► role agent that actually runs
    -----------         -----------------------------
    designer            designer
    critic              critic
    art_director        art_director
    level_designer ───► worker      (filer; the worker executes)
    tech_artist    ───► worker
    qa             ───► worker
    worker              worker
    producer            (skipped — recursive, unproductive)

Higher phases can add more dispatch rules or per-project overrides
without touching the runner.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Iterable, Literal, Optional

from .config import STUDIO_DEFAULTS
from .models import Task, TaskStatus
from .roles import RoleConfig, get_role
from .runner import LLMClient, RoleRunResult, RoleRunner
from .state import StudioState
from .tools import init_studio_unity, init_studio_vision
from .vision import VisionClient

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────── routing


DISPATCH_MAP: dict[str, Optional[str]] = {
    "designer": "designer",
    "critic": "critic",
    "art_director": "art_director",
    "audio_director": "audio_director",  # Phase 26: audio identity owner
    "audio_engineer": "audio_engineer",  # Phase 27: audio engine implementation
    "lighting_director": "lighting_director",  # Phase 28: scene lighting signature
    "camera_director": "camera_director",  # Phase 29: scene framing / composition
    "vfx_director": "vfx_director",  # Phase 30: particle systems / atmospheric VFX
    "ui_builder": "ui_builder",  # Phase 31: Canvas / Text / Button UI construction
    "build_engineer": "build_engineer",  # Phase 32: actually ship the binary
    "atmosphere_director": "atmosphere_director",  # Phase 35: skybox + fog
    "material_artist": "material_artist",  # Phase 36: PBR (metallic, smoothness, emission)
    "marketing_director": "marketing_director",  # Phase 37: press kit + PlayerSettings + hero shots
    "game_balancer": "game_balancer",  # Phase 38: playtest + perf data -> tuning tasks
    "localization_lead": "localization_lead",  # Phase 39: string tables per locale
    "tutorial_designer": "tutorial_designer",  # Phase 47: onboarding flow doc
    "scene_director": "scene_director",  # Phase 48: scene-graph + transitions doc
    "achievement_designer": "achievement_designer",  # Phase 51: unlock roster
    "storyteller": "storyteller",  # Phase 55: dialog scripts
    "level_designer": "worker",
    "tech_artist": "physics_qa",  # Phase 24: tech_artist tasks profile + optimise
    "physics_qa": "physics_qa",
    "qa": "playtester",  # Phase 23: QA tasks go to the Playtester role
    "worker": "worker",
    "playtester": "playtester",
    "producer": None,  # don't auto-dispatch back to producer; loop handles it
}


# ─────────────────────────────────────────────────────── result


DispatchAction = Literal[
    "completed",
    "blocked",
    "review",
    "skipped",
    "error",
]


@dataclass
class DispatchResult:
    """One task's outcome."""

    task_id: str
    task_title: str
    target_role: str  # may be empty when skipped before lookup
    action: DispatchAction
    reason: str = ""
    iterations: int = 0
    tool_calls: int = 0
    text: str = ""


@dataclass
class DispatchSummary:
    """Aggregate stats over a dispatch_pending() run."""

    results: list[DispatchResult] = field(default_factory=list)

    def by_action(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.results:
            counts[r.action] = counts.get(r.action, 0) + 1
        return counts

    @property
    def total(self) -> int:
        return len(self.results)


# ──────────────────────────────────────────────────── dispatcher


# Type alias for the per-role LLM factory. Production passes a constant
# function returning the same Anthropic client; dry-run passes a lambda
# that builds a fresh RehearsalLLM keyed by role id.
ClientFactory = Callable[[str], LLMClient]


class Dispatcher:
    """Picks tasks from the backlog and runs the right role per task."""

    def __init__(
        self,
        state: StudioState,
        client_factory: ClientFactory,
        *,
        unity_bridge: Optional[object] = None,
        vision_client: Optional[VisionClient] = None,
        max_iterations: int = STUDIO_DEFAULTS.max_worker_iterations,
    ):
        self.state = state
        self.client_factory = client_factory
        self.unity = unity_bridge
        self.vision = vision_client
        self.max_iterations = max_iterations
        # Wire the engine + vision bridges into studio tools once so
        # studio_capture_screenshot / studio_compare_to_reference can find them.
        if unity_bridge is not None:
            init_studio_unity(unity_bridge)
        if vision_client is not None:
            init_studio_vision(vision_client)

    # ---- routing helpers ----

    def _resolve_target(self, task: Task) -> tuple[Optional[RoleConfig], str]:
        """Return (target role config, reason-on-skip) for a task."""
        target_id = DISPATCH_MAP.get(task.role)
        if target_id is None:
            return None, f"no dispatch rule for role={task.role!r}"
        try:
            return get_role(target_id), ""
        except KeyError:
            return None, f"unknown target role {target_id!r}"

    def _can_run(self, role: RoleConfig) -> tuple[bool, str]:
        if role.needs_engine and self.unity is None:
            return False, "engine bridge not available"
        # Vision is soft: missing → tools error politely; we still let the run proceed.
        return True, ""

    @staticmethod
    def _build_brief(task: Task, role: RoleConfig) -> str:
        # Substitute {task_id} placeholders in the description with the real
        # task id. Level Designer prompts agents to write task descriptions
        # with literal "{task_id}" markers (e.g. in a final
        # studio_update_task_status call); we resolve them here so the
        # Worker can copy the spec verbatim.
        description = (task.description or "(none)").replace("{task_id}", task.id)
        ctx = (
            f"Backlog task to handle now.\n\n"
            f"Task id: {task.id}\n"
            f"Title: {task.title}\n"
            f"Description: {description}\n"
            f"Owning role: {task.role}\n"
            f"Milestone: {task.milestone or '(none)'}\n\n"
        )
        if role.id == "worker":
            return ctx + (
                "Execute this task now. Snapshot first, do the smallest scoped "
                "change, save, verify with a screenshot (and vision compare if "
                "the description names a reference), then mark this task "
                "'done' or 'blocked' via studio_update_task_status."
            )
        return ctx + (
            f"Pick this up as the {role.name}. Make the smallest improvement "
            "the description asks for. Update studio_update_task_status to "
            "'done' or 'review' when finished, and end with a 2-line summary."
        )

    # ---- main entry points ----

    def dispatch_one(self, task: Task) -> DispatchResult:
        role, reason = self._resolve_target(task)
        if role is None:
            return DispatchResult(
                task_id=task.id,
                task_title=task.title,
                target_role=task.role,
                action="skipped",
                reason=reason,
            )
        runnable, why_not = self._can_run(role)
        if not runnable:
            return DispatchResult(
                task_id=task.id,
                task_title=task.title,
                target_role=role.id,
                action="skipped",
                reason=why_not,
            )

        # Mark in_progress before running so concurrent dashboards see it.
        task.status = TaskStatus.IN_PROGRESS
        self.state.update_task(task)

        try:
            client = self.client_factory(role.id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("client_factory failed for role %s", role.id)
            return DispatchResult(
                task_id=task.id,
                task_title=task.title,
                target_role=role.id,
                action="error",
                reason=f"client_factory error: {exc}",
            )

        runner = RoleRunner(client, max_iterations=self.max_iterations, state=self.state)
        try:
            result: RoleRunResult = runner.run(role, self._build_brief(task, role))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Runner failed during dispatch of task %s", task.id)
            return DispatchResult(
                task_id=task.id,
                task_title=task.title,
                target_role=role.id,
                action="error",
                reason=f"runner error: {exc}",
            )

        # Reconcile: read the task from disk; the role agent should have
        # flipped its status. If it did not, pin it to "review" so a
        # human/Critic decides instead of leaving stale in_progress.
        latest = next((t for t in self.state.load_tasks() if t.id == task.id), None)
        if latest is None:
            return DispatchResult(
                task_id=task.id,
                task_title=task.title,
                target_role=role.id,
                action="error",
                reason="task vanished from backlog during dispatch",
                iterations=result.iterations,
                tool_calls=len(result.tool_calls),
                text=result.text,
            )
        if latest.status is TaskStatus.IN_PROGRESS:
            latest.status = TaskStatus.REVIEW
            self.state.update_task(latest)

        action: DispatchAction
        if latest.status is TaskStatus.DONE:
            action = "completed"
        elif latest.status is TaskStatus.BLOCKED:
            action = "blocked"
        elif latest.status is TaskStatus.REVIEW:
            action = "review"
        elif latest.status is TaskStatus.REJECTED:
            action = "blocked"
        else:
            action = "review"

        return DispatchResult(
            task_id=task.id,
            task_title=task.title,
            target_role=role.id,
            action=action,
            iterations=result.iterations,
            tool_calls=len(result.tool_calls),
            text=result.text,
        )

    def dispatch_pending(
        self,
        limit: int = STUDIO_DEFAULTS.max_tasks_per_producer_run,
        only_roles: Optional[Iterable[str]] = None,
    ) -> DispatchSummary:
        """Dispatch up to `limit` PENDING tasks, oldest first.

        `only_roles` narrows the queue to specific filer roles (e.g.
        only run designer-owned tasks). Default is all roles allowed by
        DISPATCH_MAP.
        """
        summary = DispatchSummary()
        wanted = set(only_roles) if only_roles else None
        for task in self.state.load_tasks():
            if task.status is not TaskStatus.PENDING:
                continue
            if wanted is not None and task.role not in wanted:
                continue
            result = self.dispatch_one(task)
            summary.results.append(result)
            if len(summary.results) >= max(1, int(limit)):
                break
        return summary
