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


def dispatch(line: str) -> CommandResult:
    """Parse one slash-command line and dispatch.

    Caller has already stripped the leading '/'.
    Returns CommandResult(handled=False) for unknown commands so the
    REPL can fall through.
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
