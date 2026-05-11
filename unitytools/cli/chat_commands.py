"""Phase 59: deterministic slash-command layer for the chat REPL.

The chat REPL routes non-slash messages to the LLM, which then picks
tools via tool-calling. That's flexible but non-deterministic — for
the SAME phrase gemma4 might pick studio_dashboard or studio_get_summary
depending on context. For common operations the operator wants
to fire the EXACT tool every time, slash commands bypass the LLM.

This module is the pure-Python dispatcher: takes a parsed command
+ args, runs the right studio tool, returns a (success, result_dict,
rich_renderable) triple the REPL prints. No side effects on stdout
inside this module — keeps it unit-testable without capturing
console output.
"""
from __future__ import annotations

import logging
import shlex
from dataclasses import dataclass
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────── command result type


@dataclass
class CommandResult:
    """The outcome of one slash command dispatch."""

    handled: bool                # True if we recognised the command
    ok: bool = True              # True if the action succeeded
    tool_name: Optional[str] = None
    tool_result: Optional[dict] = None
    message: str = ""            # Human-readable summary line
    quit: bool = False           # True iff the caller should exit the REPL


@dataclass
class DispatchContext:
    """Runtime context for slash commands that need infrastructure
    (LLM client + Unity bridge). The chat REPL builds one of these
    at start time + passes it to dispatch() so /dispatch can run
    role agents end-to-end.
    """

    config: Any = None       # unitytools.core.config.Config
    unity_bridge: Any = None  # unitytools.bridges.UnityBridge or None


# ─────────────────────────────────────────────── public entry point


_SCAFFOLDER_BY_GENRE: dict[str, Callable[..., dict]] = {}


def _load_scaffolders() -> dict[str, Callable[..., dict]]:
    """Lazily resolve scaffolder functions so importing this module
    doesn't pay the studio-import cost when chat isn't running."""
    if _SCAFFOLDER_BY_GENRE:
        return _SCAFFOLDER_BY_GENRE
    from ..studio.tools import (
        studio_scaffold_collectathon_game,
        studio_scaffold_endless_runner_game,
        studio_scaffold_platformer_game,
        studio_scaffold_top_down_shooter_game,
    )
    _SCAFFOLDER_BY_GENRE.update({
        "collectathon": studio_scaffold_collectathon_game,
        "collect": studio_scaffold_collectathon_game,
        "shooter": studio_scaffold_top_down_shooter_game,
        "topdown": studio_scaffold_top_down_shooter_game,
        "wave": studio_scaffold_top_down_shooter_game,
        "runner": studio_scaffold_endless_runner_game,
        "endless": studio_scaffold_endless_runner_game,
        "platformer": studio_scaffold_platformer_game,
        "platform": studio_scaffold_platformer_game,
        "jump": studio_scaffold_platformer_game,
    })
    return _SCAFFOLDER_BY_GENRE


_AUDIT_BY_KIND: dict[str, str] = {
    "lighting": "studio_lighting_audit",
    "atmosphere": "studio_atmosphere_audit",
    "sky": "studio_atmosphere_audit",
    "fog": "studio_atmosphere_audit",
    "vfx": "studio_vfx_audit",
    "particle": "studio_vfx_audit",
    "build": "studio_build_check",
    "consistency": "studio_internal_consistency_check",
    "drift": "studio_internal_consistency_check",
    "balance": "studio_balance_audit",
    "playtest": "studio_balance_audit",
    "ship": "studio_ship_readiness_check",
    "release": "studio_ship_readiness_check",
    "localization": "studio_localization_audit",
    "locale": "studio_localization_audit",
}


def dispatch(line: str, ctx: Optional["DispatchContext"] = None) -> CommandResult:
    """Parse one slash-command line and dispatch.

    Caller has already stripped the leading '/'.
    Returns CommandResult(handled=False) for unknown commands so the
    REPL can fall through.

    ctx (optional) provides the runtime context for commands that
    need an LLM client + Unity bridge (currently /dispatch). When
    omitted, those commands return a 'context unavailable' error
    without crashing.
    """
    try:
        parts = shlex.split(line)
    except ValueError:
        # Mismatched quotes — keep going with whitespace split
        parts = line.split()
    if not parts:
        return CommandResult(handled=False)
    cmd = parts[0].lower()
    args = parts[1:]

    # ── exit
    if cmd in ("quit", "exit", "q"):
        return CommandResult(handled=True, ok=True, message="Goodbye.", quit=True)

    # ── scaffold <genre> [name] [count]
    if cmd == "scaffold":
        return _dispatch_scaffold(args)

    # ── dashboard [--save] [--days N]
    if cmd == "dashboard":
        return _dispatch_dashboard(args)

    # ── ship  (alias for ship_readiness_check)
    if cmd == "ship":
        return _run_no_arg_tool("studio_ship_readiness_check", "Ship readiness")

    # ── cost [days]
    if cmd == "cost":
        return _dispatch_cost(args)

    # ── audit <kind>
    if cmd == "audit":
        return _dispatch_audit(args)

    # ── tasks [status]
    if cmd == "tasks":
        return _dispatch_tasks(args)

    # ── milestones
    if cmd in ("milestones", "ms"):
        return _run_no_arg_tool("studio_list_milestones", "Milestones")

    # ── decisions
    if cmd == "decisions":
        return _run_no_arg_tool("studio_list_decisions", "Decisions")

    # ── refs   (list studio/refs/)
    if cmd == "refs":
        return _run_no_arg_tool("studio_list_references", "References")

    # ── screenshots   (list studio/qa/screenshots/)
    if cmd in ("screenshots", "shots"):
        return _run_no_arg_tool("studio_list_screenshots", "Screenshots")

    # ── locales   (list studio/strings/<code>.json)
    if cmd == "locales":
        return _run_no_arg_tool("studio_list_locales", "Locales")

    # ── dialogs   (list studio/dialogs/<id>.json)
    if cmd == "dialogs":
        return _run_no_arg_tool("studio_list_dialogs", "Dialogs")

    # ── assets   (asset manifest: refs / audio-refs / shots / generated / builds)
    if cmd == "assets":
        return _run_no_arg_tool("studio_asset_manifest", "Asset manifest")

    # ── behaviours [filter]
    if cmd in ("behaviours", "behaviors"):
        return _dispatch_behaviours(args)

    # ── roles
    if cmd == "roles":
        return _dispatch_roles()

    # ── init [project-path]
    if cmd == "init":
        return _dispatch_init(args)

    # ── diag   (quick infra checks)
    if cmd == "diag":
        return _dispatch_diag()

    # ── dispatch [limit] [--only role1,role2] [--dry-run]
    if cmd == "dispatch":
        return _dispatch_autopilot(args, ctx)

    # ── sync [--check]   bring studio up to current schema
    if cmd == "sync":
        return _dispatch_sync(args)

    # ── role <role-id> <brief>   run one specific role one-shot
    if cmd == "role":
        return _dispatch_role(args, ctx)

    return CommandResult(handled=False)


# ─────────────────────────────────────────────── individual handlers


def _dispatch_scaffold(args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message="Usage: /scaffold <collectathon|shooter|runner|platformer> [name]"
        )
    genre_key = args[0].lower()
    scaffolders = _load_scaffolders()
    fn = scaffolders.get(genre_key)
    if fn is None:
        return CommandResult(
            handled=True, ok=False,
            message=(
                f"Unknown genre {genre_key!r}. "
                f"Choices: {sorted(set(scaffolders.keys()))}"
            ),
        )
    # Remaining args = display name (join so "Coin Hunter" survives)
    name = " ".join(args[1:]).strip()
    kwargs: dict[str, Any] = {}
    if name:
        kwargs["game_name"] = name
    try:
        result = fn(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name=fn.__name__,
            message=f"scaffold failed: {exc}",
        )
    ok = bool(result.get("ok"))
    if ok:
        msg = (
            f"Scaffolded {genre_key!r} -> {result.get('task_count', 0)} tasks "
            f"opened, milestone id={result.get('milestone_id', '?')}"
        )
    else:
        msg = f"Scaffold rejected: {result.get('error', '?')}"
    return CommandResult(
        handled=True, ok=ok, tool_name=fn.__name__,
        tool_result=result, message=msg,
    )


def _dispatch_dashboard(args: list[str]) -> CommandResult:
    save = False
    days = 7
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--save", "-s"):
            save = True
            i += 1
        elif a in ("--days", "-d") and i + 1 < len(args):
            try:
                days = max(1, int(args[i + 1]))
            except ValueError:
                pass
            i += 2
        elif a.isdigit():
            days = max(1, int(a))
            i += 1
        else:
            i += 1
    from ..studio.tools import studio_dashboard
    try:
        result = studio_dashboard(days=days, save_report=save)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(handled=True, ok=False,
                              tool_name="studio_dashboard",
                              message=f"dashboard failed: {exc}")
    ok = bool(result.get("ok"))
    if ok:
        headline = result.get("headline", "?")
        blocker_count = len(result.get("blockers", []))
        suffix = f" -> {result.get('saved_path')}" if save and result.get("saved_path") else ""
        msg = f"Dashboard: {headline} ({blocker_count} blockers, {days}d window){suffix}"
    else:
        msg = f"dashboard error: {result.get('error', '?')}"
    return CommandResult(handled=True, ok=ok, tool_name="studio_dashboard",
                          tool_result=result, message=msg)


def _dispatch_cost(args: list[str]) -> CommandResult:
    days = 7
    if args and args[0].isdigit():
        days = max(0, int(args[0]))
    from ..studio.tools import studio_cost_summary
    try:
        result = studio_cost_summary(days=days)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(handled=True, ok=False,
                              tool_name="studio_cost_summary",
                              message=f"cost summary failed: {exc}")
    msg = (
        f"Cost ({days}d): {result.get('total_calls', 0)} calls, "
        f"${result.get('total_cost_usd', 0.0):.4f} USD"
    )
    return CommandResult(handled=True, ok=True, tool_name="studio_cost_summary",
                          tool_result=result, message=msg)


def _dispatch_audit(args: list[str]) -> CommandResult:
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message=f"Usage: /audit <{'|'.join(sorted(set(_AUDIT_BY_KIND.values())))}>"
        )
    kind_key = args[0].lower()
    tool_name = _AUDIT_BY_KIND.get(kind_key)
    if tool_name is None:
        return CommandResult(
            handled=True, ok=False,
            message=f"Unknown audit kind {kind_key!r}. "
                    f"Choices: {sorted(set(_AUDIT_BY_KIND.keys()))}"
        )
    return _run_no_arg_tool(tool_name, f"{kind_key} audit")


def _dispatch_tasks(args: list[str]) -> CommandResult:
    from ..studio.tools import studio_list_tasks
    kwargs: dict[str, Any] = {}
    if args:
        kwargs["status"] = args[0]
    try:
        result = studio_list_tasks(**kwargs)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(handled=True, ok=False,
                              tool_name="studio_list_tasks",
                              message=f"list tasks failed: {exc}")
    msg = f"Tasks: {result.get('count', 0)} matching"
    return CommandResult(handled=True, ok=True,
                          tool_name="studio_list_tasks",
                          tool_result=result, message=msg)


def _dispatch_behaviours(args: list[str]) -> CommandResult:
    """List the 30-entry Behaviour Library, optionally substring-filtered."""
    try:
        from ..tools.unity_tools import _BEHAVIOUR_LIBRARY
    except ImportError:
        return CommandResult(
            handled=True, ok=False,
            message="unitytools.tools.unity_tools not importable.",
        )
    needle = " ".join(args).strip().lower()
    rows = [b for b in _BEHAVIOUR_LIBRARY
             if not needle or needle in b.lower()]
    summary_lines = ", ".join(rows[:10])
    if len(rows) > 10:
        summary_lines += f", ... (+{len(rows) - 10} more)"
    return CommandResult(
        handled=True, ok=True,
        tool_name="unity_list_behaviour_library",
        tool_result={"matches": rows, "total": len(_BEHAVIOUR_LIBRARY)},
        message=(
            f"Behaviour library ({len(rows)} of {len(_BEHAVIOUR_LIBRARY)}"
            + (f" matching '{needle}'" if needle else "")
            + f"): {summary_lines}"
        ),
    )


def _dispatch_roles() -> CommandResult:
    """List every studio role + its tool count."""
    try:
        from ..studio import all_roles
    except ImportError:
        return CommandResult(
            handled=True, ok=False,
            message="unitytools.studio not importable.",
        )
    rows = sorted(
        [(r.id, r.name, len(r.allowed_tools), r.needs_engine, r.needs_vision)
         for r in all_roles()],
        key=lambda x: x[0],
    )
    summary = f"{len(rows)} roles: " + ", ".join(r[0] for r in rows[:6])
    if len(rows) > 6:
        summary += f", ... (+{len(rows) - 6} more)"
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio.all_roles",
        tool_result={
            "count": len(rows),
            "roles": [
                {"id": r[0], "name": r[1], "tool_count": r[2],
                 "needs_engine": r[3], "needs_vision": r[4]}
                for r in rows
            ],
        },
        message=summary,
    )


def _dispatch_init(args: list[str]) -> CommandResult:
    """Scaffold a fresh studio/ directory in the cwd (or a given path)."""
    from pathlib import Path
    from ..studio import StudioPaths, StudioState
    from ..studio.templates import starter_files

    project_root = Path(args[0]).expanduser().resolve() if args else Path.cwd().resolve()
    if not project_root.exists():
        return CommandResult(
            handled=True, ok=False,
            message=f"Path does not exist: {project_root}",
        )

    paths = StudioPaths(project_root=project_root)
    if paths.exists():
        # Already initialised — just report
        return CommandResult(
            handled=True, ok=True,
            tool_name="studio_init",
            tool_result={"project_root": str(project_root),
                          "already_initialised": True},
            message=f"Studio already exists at {paths.root}",
        )

    # Create all canonical directories
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)

    # Drop the starter docs
    files_written: list[str] = []
    for rel_path, content in starter_files().items():
        target = paths.root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(content, encoding="utf-8")
            files_written.append(rel_path)

    # Initial empty state files via StudioState helpers
    state = StudioState(paths)
    state.save_tasks([])  # writes backlog.json if missing
    state.save_milestones([])

    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_init",
        tool_result={
            "project_root": str(project_root),
            "studio_root": str(paths.root),
            "files_written": files_written,
        },
        message=(
            f"Studio scaffolded at {paths.root} -- "
            f"{len(files_written)} starter files, "
            f"{len(paths.all_dirs())} directories. "
            "Restart chat to pick up the new studio state."
        ),
    )


def _dispatch_diag() -> CommandResult:
    """Quick infrastructure summary: tool count, studio active, registry size."""
    try:
        from ..core.tool_registry import get_all_tools
        from ..studio import all_roles
        from ..tools.unity_tools import _BEHAVIOUR_LIBRARY
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"Import failed: {exc}",
        )
    tools = get_all_tools()
    studio_tools = [t for t in tools if t.name.startswith("studio_")]
    unity_tools = [t for t in tools if t.name.startswith("unity_")]

    info = {
        "total_tools": len(tools),
        "studio_tools": len(studio_tools),
        "unity_tools": len(unity_tools),
        "roles": len(all_roles()),
        "behaviour_library_size": len(_BEHAVIOUR_LIBRARY),
    }
    msg = (
        f"Tools: {info['total_tools']} ({info['studio_tools']} studio_*, "
        f"{info['unity_tools']} unity_*) | "
        f"Roles: {info['roles']} | "
        f"Behaviours: {info['behaviour_library_size']}"
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="diag",
        tool_result=info,
        message=msg,
    )


def _dispatch_role(args: list[str], ctx: Optional[DispatchContext]) -> CommandResult:
    """/role <role-id> [brief]

    Runs ONE specific role one-shot through a fresh RoleRunner.
    Uses the configured LLM client. Wires engine + vision bridges
    automatically when the role needs them. brief is the rest of
    the line; if omitted, the role's default brief from CLI is used.
    """
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message="Usage: /role <role-id> [brief]   e.g. /role designer 'Draft GDD'",
        )

    role_id = args[0]
    brief = " ".join(args[1:]).strip()

    # Validate role
    try:
        from ..studio import get_role
        try:
            role = get_role(role_id)
        except KeyError:
            from ..studio import all_roles
            available = sorted(r.id for r in all_roles())
            return CommandResult(
                handled=True, ok=False,
                message=f"Unknown role {role_id!r}. Available: {available}",
            )
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio package not importable: {exc}",
        )

    # Validate active state
    try:
        from ..studio.tools import _STATE
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio tools not importable: {exc}",
        )
    if _STATE is None:
        return CommandResult(
            handled=True, ok=False,
            message="No active studio. Run /init first or `cd` into a Unity project.",
        )

    # Need a context for the LLM client
    if ctx is None or ctx.config is None:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "/role needs a runtime context (LLM client + config). "
                "REPL didn't pass one. (Use the chat REPL — direct API has no LLM wiring.)"
            ),
        )

    # Pick a default brief if none given (mirrors `unitytools studio-run` defaults)
    if not brief:
        brief = _default_brief_for_role(role.id)

    # Build LLM client
    try:
        from ..studio import (
            RoleRunner,
            make_default_client,
            make_default_vision_client,
        )
        from ..studio.tools import init_studio_unity, init_studio_vision
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"Studio runner imports failed: {exc}",
        )

    try:
        client = make_default_client(ctx.config)
    except RuntimeError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"LLM client setup failed: {exc}",
        )

    # Engine + vision wiring (when the role needs them)
    if role.needs_engine and ctx.unity_bridge is not None:
        try:
            if ctx.unity_bridge.connect(timeout=2.0):
                init_studio_unity(ctx.unity_bridge)
        except Exception:  # noqa: BLE001
            pass
    if role.needs_vision:
        try:
            v = make_default_vision_client(ctx.config)
            init_studio_vision(v)
        except RuntimeError:
            pass   # role tools error politely when vision unavailable

    # Run the role
    thresholds = _STATE.thresholds
    runner = RoleRunner(
        client,
        max_iterations=thresholds.max_worker_iterations,
        state=_STATE,
    )
    try:
        result = runner.run(role, brief)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name=f"role:{role.id}",
            message=f"Role {role.id!r} run failed: {exc}",
        )

    tool_call_count = len(result.tool_calls)
    text_preview = (result.text or "").strip().splitlines()[:3]
    text_summary = " / ".join(line.strip() for line in text_preview if line.strip())
    if len(text_summary) > 160:
        text_summary = text_summary[:157] + "..."

    msg = (
        f"Role {role.id!r} done -- {result.iterations} iter, "
        f"{tool_call_count} tool call(s), stop={result.stop_reason}"
    )
    if text_summary:
        msg += f"\n  text: {text_summary}"
    return CommandResult(
        handled=True, ok=True,
        tool_name=f"role:{role.id}",
        tool_result={
            "role_id": role.id,
            "brief": brief,
            "iterations": result.iterations,
            "tool_calls": [
                {"name": tc.name, "ok": tc.ok}
                for tc in result.tool_calls
            ],
            "stop_reason": result.stop_reason,
            "text": result.text,
        },
        message=msg,
    )


def _default_brief_for_role(role_id: str) -> str:
    """Mirror the CLI's _default_brief_for_role table so chat /role
    uses the same sensible defaults when the user omits a brief."""
    table = {
        "producer": "Plan the next round of work. Read state, decide priorities, open up to 5 tasks.",
        "designer": "Read the current GDD and produce the smallest coherent improvement.",
        "critic": "Review the project for inconsistency between GDD, art bible, and recent decisions.",
        "level_designer": "Pick a reference from studio/refs/, compare to current scene, file follow-up tasks.",
        "art_director": "Audit current scene palette against the dominant reference and Art Bible.",
        "playtester": "Run a 3-second smoke playtest on the current scene.",
        "physics_qa": "Profile the current scene against perf budgets.",
        "audio_director": "Refine the Audio Brief in line with the GDD pitch.",
        "audio_engineer": "Import audio + attach AudioSource as the task describes.",
        "lighting_director": "Audit + tune scene lighting against the Art Bible palette.",
        "camera_director": "Frame the main camera on the target named in the task.",
        "vfx_director": "Audit particle systems against budgets and tune offenders.",
        "ui_builder": "Build the UI named in the task.",
        "build_engineer": "Run studio_ship_readiness_check; if pass, build the configured target.",
        "atmosphere_director": "Tune skybox + fog to match Art Bible palette and mood.",
        "material_artist": "Tune PBR on the target named in the task.",
        "marketing_director": "Finalise press kit + PlayerSettings; capture a hero shot.",
        "game_balancer": "Run studio_balance_audit and file specific tuning tasks.",
        "localization_lead": "Audit studio/strings/ coverage; fill gaps.",
        "tutorial_designer": "Refine studio/tutorial.md with player goal + controls + beats.",
        "scene_director": "Refine studio/scene_catalog.md with scene graph + transitions.",
        "achievement_designer": "Refine studio/achievements.md roster.",
        "storyteller": "Draft a dialog script for the moment named in the task.",
        "worker": "Execute this task now per the description; snapshot first, save, status update last.",
    }
    return table.get(role_id, "Run your role on the current project state.")


def _dispatch_sync(args: list[str]) -> CommandResult:
    """/sync [--check] — migrate the active studio to current schema."""
    check_only = any(a in ("--check", "-c", "--dry") for a in args)
    try:
        from ..studio.tools import studio_sync
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_sync not importable: {exc}",
        )
    try:
        result = studio_sync(check_only=check_only)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_sync",
            message=f"sync failed: {exc}",
        )
    if result["in_sync"]:
        msg = (
            f"In sync ({result['schema_info']['expected_doc_count']} docs / "
            f"{result['schema_info']['behaviour_library_size']} behaviours / "
            f"{result['schema_info']['role_count']} roles current)."
        )
    elif check_only:
        msg = (
            f"{result['drift_count']} drift item(s): "
            f"{len(result['missing_files'])} files, "
            f"{len(result['missing_dirs'])} dirs missing. "
            "Run /sync to apply."
        )
    else:
        msg = (
            f"Applied {len(result['actions_applied'])} migration step(s)."
        )
    return CommandResult(
        handled=True, ok=True, tool_name="studio_sync",
        tool_result=result, message=msg,
    )


def _dispatch_autopilot(args: list[str], ctx: Optional[DispatchContext]) -> CommandResult:
    """/dispatch [limit] [--only r1,r2] [--dry-run]

    Walks the backlog and runs each pending task's role. limit caps
    the number of tasks (default 5). --only filters to specific
    originating role ids. --dry-run uses RehearsalLLM (no API calls,
    skips engine-dependent roles).
    """
    # Parse args
    limit = 5
    only_roles: Optional[tuple[str, ...]] = None
    dry_run = False
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--dry-run", "--dry"):
            dry_run = True
            i += 1
        elif a in ("--only", "-o") and i + 1 < len(args):
            only_roles = tuple(r.strip() for r in args[i + 1].split(",") if r.strip())
            i += 2
        elif a.isdigit():
            limit = max(1, int(a))
            i += 1
        elif a.lstrip("-").isdigit() and a.startswith("-"):
            # Negative number? Treat as positive.
            limit = max(1, abs(int(a)))
            i += 1
        else:
            i += 1
    if limit > 50:
        return CommandResult(
            handled=True, ok=False,
            message=f"limit {limit} > 50 — autopilot caps at 50 tasks per run. "
                    "Run /dispatch repeatedly if you need more.",
        )

    # Need a studio state to dispatch into
    try:
        from ..studio.tools import _STATE
    except ImportError:
        return CommandResult(
            handled=True, ok=False,
            message="studio package not importable.",
        )
    if _STATE is None:
        return CommandResult(
            handled=True, ok=False,
            message="No active studio. Run /init first (or restart chat in a "
                    "directory containing studio/).",
        )

    # Build the client factory + bridge
    try:
        from ..studio import (
            Dispatcher,
            RehearsalLLM,
            has_rehearsal_for,
            make_default_client,
            make_default_vision_client,
        )
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"Studio runner imports failed: {exc}",
        )

    bridge_for_dispatcher = None
    vision_for_dispatcher = None
    if dry_run:
        def client_factory(role_id: str):
            return RehearsalLLM(role_id)
    else:
        if ctx is None or ctx.config is None:
            return CommandResult(
                handled=True, ok=False,
                message="/dispatch needs a runtime context (LLM client + config). "
                        "This usually means the chat REPL didn't pass one. "
                        "Try /dispatch --dry-run for a no-network rehearsal.",
            )
        try:
            shared_client = make_default_client(ctx.config)
        except RuntimeError as exc:
            return CommandResult(
                handled=True, ok=False,
                message=f"LLM client setup failed: {exc}",
            )

        def client_factory(role_id: str):
            return shared_client

        # Optional engine + vision wiring
        if ctx.unity_bridge is not None:
            try:
                if ctx.unity_bridge.connect(timeout=2.0):
                    bridge_for_dispatcher = ctx.unity_bridge
            except Exception:  # noqa: BLE001
                pass
        try:
            vision_for_dispatcher = make_default_vision_client(ctx.config)
        except RuntimeError:
            vision_for_dispatcher = None

    # Build + run the dispatcher
    thresholds = _STATE.thresholds
    dispatcher = Dispatcher(
        _STATE,
        client_factory,
        unity_bridge=bridge_for_dispatcher,
        vision_client=vision_for_dispatcher,
        max_iterations=thresholds.max_worker_iterations,
    )

    try:
        summary = dispatcher.dispatch_pending(limit=limit, only_roles=only_roles)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio.dispatch_pending",
            message=f"dispatch failed: {exc}",
        )

    # Aggregate the result counts
    counts = summary.by_action()
    pieces = [f"{action}={count}" for action, count in sorted(counts.items())]
    summary_line = ", ".join(pieces) if pieces else "no tasks matched"
    mode = "dry-run" if dry_run else "live"
    filter_note = f" [only={','.join(only_roles)}]" if only_roles else ""
    msg = (
        f"Dispatched {summary.total} tasks ({mode}{filter_note}): {summary_line}"
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio.dispatch_pending",
        tool_result={
            "total": summary.total,
            "counts": counts,
            "results": [
                {"task_id": r.task_id, "target_role": r.target_role,
                 "action": r.action, "iterations": r.iterations,
                 "tool_calls": r.tool_calls}
                for r in summary.results
            ],
            "dry_run": dry_run,
            "limit": limit,
            "only_roles": list(only_roles) if only_roles else None,
        },
        message=msg,
    )


def _run_no_arg_tool(tool_name: str, label: str) -> CommandResult:
    """Call a studio tool that takes no arguments + summarise."""
    from ..core.tool_registry import get_tool
    spec = get_tool(tool_name)
    if spec is None:
        return CommandResult(handled=True, ok=False, tool_name=tool_name,
                              message=f"{tool_name} not in registry. "
                                      "(Did studio init fail?)")
    try:
        result = spec.fn()
    except Exception as exc:  # noqa: BLE001
        return CommandResult(handled=True, ok=False, tool_name=tool_name,
                              message=f"{label} failed: {exc}")
    if not isinstance(result, dict):
        return CommandResult(handled=True, ok=True, tool_name=tool_name,
                              tool_result=None,
                              message=f"{label}: {result!r}")
    ok = result.get("ok", True) is not False
    verdict = result.get("verdict")
    if verdict:
        msg = f"{label}: verdict={verdict}"
        if result.get("violations") or result.get("blockers") or result.get("drifts"):
            problems = (result.get("violations") or result.get("blockers")
                         or result.get("drifts") or [])
            msg += f" ({len(problems)} issues)"
    else:
        count = result.get("count") or result.get("task_count") or 0
        msg = f"{label}: {count}" if count else f"{label}: ok"
    return CommandResult(handled=True, ok=ok, tool_name=tool_name,
                          tool_result=result, message=msg)
