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


# Phase 65: Turkish slash-command aliases. The operator types in
# Turkish; commands should match. Each Turkish key resolves to its
# canonical English equivalent BEFORE the dispatch switch runs.
# Both forms work; /help shows the English form by default.
_ALIASES: dict[str, str] = {
    # Meta
    "yardım": "help", "yardim": "help",
    "temizle": "clear",
    "araç": "tools", "araclar": "tools", "araçlar": "tools",
    "durum": "status",
    "sağlık": "diag", "saglik": "diag",
    "çıkış": "quit", "cikis": "quit", "çık": "quit", "cik": "quit",
    # Studio actions
    "başlat": "init", "baslat": "init",
    "eşitle": "sync", "esitle": "sync", "güncel": "sync", "guncel": "sync",
    "oluştur": "scaffold", "olustur": "scaffold", "kur": "scaffold",
    "yürüt": "dispatch", "yurut": "dispatch", "yur": "dispatch",
    "rol": "role",
    "rapor": "dashboard", "panel": "dashboard",
    "satış": "ship", "satis": "ship", "yayın": "ship", "yayin": "ship",
    "maliyet": "cost", "masraf": "cost",
    "denetim": "audit", "tarama": "audit",
    "yapı": "build", "yapi": "build", "derle": "build", "inşa": "build", "insa": "build",
    # Phase 69 producer-flow shortcuts
    "sprint": "sprint",  # English passthrough (no Turkish word commonly used)
    "sıradaki": "next", "siradaki": "next", "sıra": "next", "sira": "next",
    "sonraki": "next",
    # Phase 70 task lifecycle
    "al": "take", "üstlen": "take", "ustlen": "take",
    "tamam": "done", "bitti": "done", "bitir": "done",
    "engelle": "block", "blokla": "block",
    "aç": "unblock", "ac": "unblock", "çöz": "unblock", "coz": "unblock",
    "neden": "why", "niçin": "why", "nicin": "why",
    # Phase 71 standup digest
    "toplantı": "standup", "toplanti": "standup",
    "özet": "standup", "ozet": "standup",
    "günbaşı": "standup", "gunbasi": "standup",
    # Phase 72 journal
    "not": "log", "kayıt": "log", "kayit": "log",
    "günlük": "journal", "gunluk": "journal",
    "geçmiş": "journal", "gecmis": "journal",
    # Phase 73 decide
    "karar": "decide", "karara": "decide",
    # Phase 75 cross-studio search
    "bul": "find", "ara": "find", "arama": "find",
    # Phase 76 burndown
    "ilerleme": "burndown", "yakım": "burndown", "yakim": "burndown",
    "grafik": "burndown",
    # Phase 79 commit
    "kaydet": "commit", "işle": "commit", "isle": "commit",
    "gönder": "commit", "gonder": "commit",
    # Phase 80 task editing
    "açıklama": "note", "aciklama": "note", "ekle": "note",
    "bağımlı": "dep", "bagimli": "dep", "bağ": "dep", "bag": "dep",
    "bekler": "dep",
    # Phase 81 recent activity timeline
    "son": "recent", "sondurum": "recent", "geçenler": "recent",
    "gecenler": "recent", "akış": "recent", "akis": "recent",
    # Phase 82 per-role drill-down
    "kim": "who", "rolün": "who", "rolun": "who",
    # Phase 83 blocked + inflight drill-downs
    "engelli": "blocked", "engellenmiş": "blocked", "engellenmis": "blocked",
    "tıkalı": "blocked", "tikali": "blocked",
    "süren": "inflight", "suren": "inflight",
    "yapılan": "inflight", "yapilan": "inflight",
    # Phase 84 backlog hygiene + planning
    "iptal": "discard", "vazgeç": "discard", "vazgec": "discard",
    "reddet": "discard",
    "kilometre": "milestone", "kilometretaşı": "milestone",
    "hedefkur": "milestone", "yenihedef": "milestone",
    # Phase 85 end-of-day wrap-up
    "günsonu": "wrap-up", "gunsonu": "wrap-up",
    "kapanış": "wrap-up", "kapanis": "wrap-up",
    "kapat": "wrap-up",
    # Phase 86 full task viewer
    "göster": "show", "goster": "show", "bak": "show", "detay": "show",
    # Inventory
    "görev": "tasks", "gorev": "tasks", "görevler": "tasks", "gorevler": "tasks",
    "hedef": "milestones", "hedefler": "milestones",
    "kararlar": "decisions",
    "referans": "refs",
    "ekran": "screenshots",
    "diller": "locales", "dil": "locales",
    "diyalog": "dialogs", "dialoglar": "dialogs", "diyaloglar": "dialogs",
    "varlık": "assets", "varlik": "assets",
    "varlıklar": "assets", "varliklar": "assets",
    "davranış": "behaviours", "davranis": "behaviours", "davranışlar": "behaviours",
    "roller": "roles",
}


def _resolve_alias(cmd: str) -> str:
    """Map a Turkish-language slash command to its canonical English
    form, or return cmd unchanged. Case-insensitive."""
    return _ALIASES.get(cmd.lower(), cmd.lower())


# Phase 78: canonical command vocabulary used for typo suggestions.
# Keep in sync with the switch in dispatch() — drift_test below verifies
# every dispatch arm appears in this list.
_CANONICAL_COMMANDS: tuple[str, ...] = (
    "quit", "exit", "q",
    "help", "tools", "status", "studio", "diag",
    "init", "sync", "scaffold", "dispatch", "role", "build",
    "dashboard", "standup", "log", "journal", "decide", "find", "burndown",
    "commit",  # Phase 79
    "note", "dep",  # Phase 80
    "recent",  # Phase 81
    "who",  # Phase 82
    "blocked", "inflight", "wip",  # Phase 83
    "discard", "reject", "milestone",  # Phase 84
    "wrap-up", "wrapup", "wrap",  # Phase 85
    "show",  # Phase 86
    "sprint", "next", "take", "done", "block", "unblock", "why",
    "ship", "cost", "audit",
    "tasks", "milestones", "ms", "decisions",
    "refs", "screenshots", "shots", "locales", "dialogs", "assets",
    "behaviours", "behaviors", "roles",
)


def suggest_command(unknown: str, max_results: int = 3) -> list[str]:
    """Phase 78: when /<unknown> doesn't dispatch, return the closest
    known commands so chat panels can render 'did you mean...?'.

    Searches the union of canonical English commands AND every Türkçe
    alias — so /buldown gets 'burndown' suggested AND /bld gets 'bul'
    suggested. Case-insensitive via difflib's SequenceMatcher.
    Returns deduplicated canonical command names (resolving aliases),
    most-similar first. Empty list when no candidate clears the
    similarity threshold.
    """
    if not unknown:
        return []
    import difflib

    needle = unknown.lower()
    # Union of canonical + alias keys; cap the candidate pool.
    vocab = list(set(_CANONICAL_COMMANDS) | set(_ALIASES.keys()))
    raw_matches = difflib.get_close_matches(
        needle, vocab, n=max(max_results * 3, 6), cutoff=0.55,
    )

    # Resolve each match through _ALIASES so /yardım → 'help'. Dedupe
    # while preserving similarity order.
    seen: set[str] = set()
    suggestions: list[str] = []
    for m in raw_matches:
        canonical = _ALIASES.get(m, m)
        if canonical not in seen:
            seen.add(canonical)
            suggestions.append(canonical)
            if len(suggestions) >= max_results:
                break
    return suggestions


def dispatch(line: str, ctx: Optional["DispatchContext"] = None) -> CommandResult:
    """Parse one slash-command line and dispatch.

    Caller has already stripped the leading '/'.
    Returns CommandResult(handled=False) for unknown commands so the
    REPL can fall through.

    ctx (optional) provides the runtime context for commands that
    need an LLM client + Unity bridge (currently /dispatch). When
    omitted, those commands return a 'context unavailable' error
    without crashing.

    Turkish aliases are resolved to their English equivalents
    before the switch — so /oluştur / /yürüt / /sağlık work just
    like /scaffold / /dispatch / /diag.
    """
    try:
        parts = shlex.split(line)
    except ValueError:
        # Mismatched quotes — keep going with whitespace split
        parts = line.split()
    if not parts:
        return CommandResult(handled=False)
    cmd = _resolve_alias(parts[0])
    args = parts[1:]

    # ── exit
    if cmd in ("quit", "exit", "q"):
        return CommandResult(handled=True, ok=True, message="Goodbye.", quit=True)

    # ── help   (Phase 68: dispatcher-level so chat-server / Unity Editor
    #           users get the command listing too; REPL intercepts /help
    #           before reaching here with its own rich Panel output)
    if cmd == "help":
        return _dispatch_help()

    # ── tools [filter]   (Phase 68: list all registered tools; optional
    #                      substring filter)
    if cmd == "tools":
        return _dispatch_tools(args)

    # ── status   (Phase 68: bridge connectivity for editor users)
    if cmd == "status":
        return _dispatch_status(ctx)

    # ── studio   (Phase 68: active studio summary for editor users)
    if cmd == "studio":
        return _dispatch_studio_status()

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

    # ── build <target> [--dev] [--out PATH] [--force]
    if cmd == "build":
        return _dispatch_build(args, ctx)

    # ── sprint   (Phase 69: read sprint_current.md)
    if cmd == "sprint":
        return _dispatch_sprint()

    # ── next [role]   (Phase 69: surface the next ready pending task)
    if cmd == "next":
        return _dispatch_next(args)

    # ── take <task-id>   (Phase 70: mark a task in_progress)
    if cmd == "take":
        return _dispatch_task_status(args, "in_progress", verb="take")

    # ── done <task-id>   (Phase 70: mark a task done)
    if cmd == "done":
        return _dispatch_task_status(args, "done", verb="done")

    # ── unblock <task-id>   (Phase 70: mark blocked task back to pending)
    if cmd == "unblock":
        return _dispatch_task_status(args, "pending", verb="unblock")

    # ── block <task-id> [reason...]   (Phase 70: mark blocked + note reason)
    if cmd == "block":
        return _dispatch_block(args)

    # ── why <task-id>   (Phase 70: diagnostic for blockers + unsatisfied deps)
    if cmd == "why":
        return _dispatch_why(args)

    # ── standup [hours]   (Phase 71: morning digest — closed/in-flight/blocked)
    if cmd == "standup":
        return _dispatch_standup(args)

    # ── log <message>   (Phase 72: append a dated entry to today's journal)
    if cmd == "log":
        return _dispatch_log(args)

    # ── journal [days]   (Phase 72: read last N days of journal entries)
    if cmd == "journal":
        return _dispatch_journal(args)

    # ── decide <title> | <summary>   (Phase 73: fast decision capture)
    if cmd == "decide":
        return _dispatch_decide(args)

    # ── find <substring>   (Phase 75: cross-studio search)
    if cmd == "find":
        return _dispatch_find(args)

    # ── burndown [milestone-id]   (Phase 76: ASCII bar chart per milestone)
    if cmd == "burndown":
        return _dispatch_burndown(args)

    # ── commit <message>   (Phase 79: git add+commit + journal entry)
    if cmd == "commit":
        return _dispatch_commit(args)

    # ── note <task-id> <text>   (Phase 80: append note to task description)
    if cmd == "note":
        return _dispatch_note(args)

    # ── dep <task-id> <dep-id>   (Phase 80: wire a dependency)
    if cmd == "dep":
        return _dispatch_dep(args)

    # ── recent [days]   (Phase 81: combined activity timeline)
    if cmd == "recent":
        return _dispatch_recent(args)

    # ── who <role>   (Phase 82: per-role full status drill-down)
    if cmd == "who":
        return _dispatch_who(args)

    # ── blocked   (Phase 83: every blocked task with full reasons)
    if cmd == "blocked":
        return _dispatch_blocked()

    # ── inflight   (Phase 83: every in_progress task with owner)
    if cmd in ("inflight", "wip"):
        return _dispatch_inflight()

    # ── discard <task-id> [reason]   (Phase 84: mark task rejected)
    if cmd in ("discard", "reject"):
        return _dispatch_discard(args)

    # ── milestone <name> | <description>   (Phase 84: create milestone)
    if cmd == "milestone":
        return _dispatch_milestone(args)

    # ── wrap-up   (Phase 85: end-of-day digest paired with /standup)
    if cmd in ("wrap-up", "wrapup", "wrap"):
        return _dispatch_wrap_up()

    # ── show <task-id>   (Phase 86: full task viewer)
    if cmd == "show":
        return _dispatch_show(args)

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


def _dispatch_help() -> CommandResult:
    """Phase 68: plain-text command listing for chat-server / Unity Editor
    users (the REPL has its own rich-rendered /help).

    Returns the same set of commands the REPL panel advertises, plus the
    Türkçe alias hint, so editor users can discover the shortcut surface
    without leaving the chat.
    """
    sections: list[dict[str, Any]] = [
        {
            "title": "Meta",
            "commands": [
                ("/help", "show this list"),
                ("/tools [filter]", "list registered tools"),
                ("/status", "bridge connectivity"),
                ("/studio", "active studio summary"),
                ("/diag", "one-line diagnostics"),
                ("/quit", "exit (REPL only)"),
            ],
        },
        {
            "title": "Studio actions",
            "commands": [
                ("/init [path]", "scaffold a fresh studio/"),
                ("/sync [--check]", "bring studio up to current schema"),
                ("/scaffold <genre> [name]", "collectathon/shooter/runner/platformer"),
                ("/dispatch [N] [--dry-run]", "run pending tasks through their roles"),
                ("/role <role-id> [brief]", "run one role one-shot"),
                ("/build <target> [--dev]", "windows/mac/linux/webgl/android/ios"),
                ("/dashboard [--save] [days]", "operator's morning glance"),
                ("/standup [hours]", "daily digest: closed/in-flight/blocked/pending"),
                ("/wrap-up", "end-of-day digest (today's closures + carry-over + tomorrow's next)"),
                ("/recent [days]", "combined activity timeline (commits+tasks+decisions+journal)"),
                ("/who <role>", "per-role drill-down (in-flight/pending/blocked/done)"),
                ("/blocked", "every blocked task across the studio + reasons"),
                ("/inflight", "every in_progress task with owner (oldest-first)"),
                ("/log <message>", "append timestamped entry to today's journal"),
                ("/journal [days]", "read last N days of journal entries"),
                ("/decide <title> | <summary>", "record a design decision (proposed)"),
                ("/find <substring>", "search tasks/decisions/docs/journal at once"),
                ("/burndown [milestone-id]", "ASCII bar chart per milestone"),
                ("/commit <message>", "git add+commit + journal entry"),
                ("/sprint", "read studio/sprint_current.md"),
                ("/next [role]", "next pending task ready to pick up"),
                ("/take <id>", "mark task in_progress"),
                ("/done <id>", "mark task done"),
                ("/block <id> [reason]", "mark task blocked + note reason"),
                ("/unblock <id>", "blocked → pending"),
                ("/why <id>", "explain task status + unsatisfied deps"),
                ("/show <id>", "full task content (title + description + notes + deps)"),
                ("/note <id> <text>", "append timestamped note to task description"),
                ("/dep <id> <dep-id>", "wire dependency (first needs second done first)"),
                ("/discard <id> [reason]", "close task as REJECTED (won't do)"),
                ("/milestone <name> | <desc>", "create a milestone"),
                ("/ship", "ship readiness check"),
                ("/cost [days]", "LLM token + USD spend"),
                ("/audit <kind>", "lighting/atmosphere/vfx/build/balance/..."),
            ],
        },
        {
            "title": "Inventory",
            "commands": [
                ("/tasks [status]", "list backlog tasks"),
                ("/milestones", "list milestones"),
                ("/decisions", "list decisions"),
                ("/refs", "reference images"),
                ("/screenshots", "captured screenshots"),
                ("/locales", "string tables"),
                ("/dialogs", "dialog files"),
                ("/assets", "asset manifest (all 5 buckets)"),
                ("/behaviours [filter]", "Behaviour Library"),
                ("/roles", "all 24 studio roles"),
            ],
        },
    ]
    # Build a compact one-string summary for the message line. Editor UIs
    # can use tool_result["sections"] for richer rendering.
    lines: list[str] = []
    for sec in sections:
        lines.append(f"[{sec['title']}]")
        for name, desc in sec["commands"]:
            lines.append(f"  {name:<28} {desc}")
    lines.append("")
    lines.append(
        "Türkçe aliases: /yardım /durum /sağlık /başlat /eşitle /oluştur "
        "/yürüt /rol /rapor /satış /maliyet /denetim /yapı /sıradaki "
        "/al /tamam /engelle /aç /neden /toplantı /not /günlük /karar /bul /ilerleme "
        "/kaydet /işle /açıklama /bağımlı /son /akış /kim /engelli /süren "
        "/iptal /vazgeç /kilometre /günsonu /kapanış /göster /bak "
        "/görev /hedef /referans /dil /diyalog /varlık /davranış /roller"
    )
    msg = "\n".join(lines)
    return CommandResult(
        handled=True,
        ok=True,
        tool_name="help",
        tool_result={"ok": True, "sections": sections, "text": msg},
        message=msg,
    )


def _dispatch_tools(args: list[str]) -> CommandResult:
    """Phase 68: list registered tools, with optional substring filter.

    Mirrors the REPL `/tools [filter]` behaviour so chat-server clients
    can drive the same lookup without scrolling through 200 entries
    every time."""
    try:
        from ..core.tool_registry import get_all_tools
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False, message=f"Import failed: {exc}",
        )

    needle = " ".join(args).strip().lower()
    all_tools = get_all_tools()
    if needle:
        rows = [
            t for t in all_tools
            if needle in t.name.lower() or needle in t.description.lower()
        ]
    else:
        rows = list(all_tools)

    items = [{"name": t.name, "description": t.description} for t in rows]
    title = f"Tools matching '{needle}'" if needle else "All registered tools"
    summary = f"{title}: {len(items)} shown" + (
        f" (of {len(all_tools)} total)" if needle else ""
    )
    # Keep message compact — the structured result holds the full payload.
    preview_names = ", ".join(t.name for t in rows[:10])
    if len(rows) > 10:
        preview_names += f", ... (+{len(rows) - 10} more)"
    msg = f"{summary}. {preview_names}" if preview_names else summary
    return CommandResult(
        handled=True,
        ok=True,
        tool_name="tools",
        tool_result={
            "ok": True,
            "total": len(all_tools),
            "shown": len(items),
            "filter": needle or None,
            "tools": items,
        },
        message=msg,
    )


def _dispatch_status(ctx: Optional[DispatchContext]) -> CommandResult:
    """Phase 68: bridge + provider snapshot — what's online right now."""
    info: dict[str, Any] = {"ok": True}
    # Unity bridge from the dispatch context
    unity_state = "no-bridge"
    if ctx is not None and ctx.unity_bridge is not None:
        try:
            if hasattr(ctx.unity_bridge, "is_connected") and ctx.unity_bridge.is_connected():
                unity_state = "connected"
            else:
                unity_state = "offline"
        except Exception as exc:  # noqa: BLE001
            unity_state = f"error: {exc}"
    info["unity"] = unity_state

    # Provider/model — best-effort
    provider = "unknown"
    model = "unknown"
    if ctx is not None and ctx.config is not None:
        cfg = ctx.config
        provider = getattr(cfg, "provider", "unknown")
        model = (
            getattr(cfg, "ollama_model", None)
            if provider == "ollama"
            else getattr(cfg, "model", None)
        ) or "unknown"
    info["provider"] = provider
    info["model"] = model

    msg = f"Unity: {unity_state} | Provider: {provider} ({model})"
    return CommandResult(
        handled=True,
        ok=True,
        tool_name="status",
        tool_result=info,
        message=msg,
    )


def _dispatch_studio_status() -> CommandResult:
    """Phase 68: thin wrapper around studio_get_summary for editor users.

    REPL has its own rich Panel render; the chat-server / editor path
    gets the same dict here so its UI can show it however it likes.
    """
    try:
        from ..studio.tools import studio_get_summary
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False, message=f"Import failed: {exc}",
        )
    try:
        summary = studio_get_summary()
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False, message=f"studio_get_summary failed: {exc}",
        )
    if not summary.get("ok"):
        return CommandResult(
            handled=True,
            ok=False,
            tool_name="studio_get_summary",
            tool_result=summary,
            message=f"Studio inactive: {summary.get('error', 'unknown reason')}",
        )
    root = summary.get("studio_root", "?")
    tcount = summary.get("task_count", 0)
    mcount = summary.get("milestone_count", 0)
    dcount = summary.get("decision_count", 0)
    msg = (
        f"Studio at {root} | Tasks: {tcount} | Milestones: {mcount} | "
        f"Decisions: {dcount}"
    )
    return CommandResult(
        handled=True,
        ok=True,
        tool_name="studio_get_summary",
        tool_result=summary,
        message=msg,
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


# Mapping of build-target keyword aliases (Turkish-friendly + short) to
# the canonical Unity build-target string the bridge handler accepts.
_BUILD_TARGET_ALIASES: dict[str, str] = {
    "windows": "windows", "win": "windows", "win64": "windows",
    "exe": "windows", "windows64": "windows",
    "mac": "mac", "osx": "mac", "macos": "mac",
    "linux": "linux", "linux64": "linux",
    "webgl": "webgl", "web": "webgl", "html": "webgl", "html5": "webgl",
    "android": "android", "apk": "android",
    "ios": "ios", "iphone": "ios", "ipad": "ios",
}

_BUILD_EXTENSION: dict[str, str] = {
    "windows": ".exe",
    "mac": ".app",
    "linux": ".x86_64",
    "webgl": "/index.html",
    "android": ".apk",
    "ios": ".app",
}


def _dispatch_build(args: list[str], ctx: Optional[DispatchContext]) -> CommandResult:
    """/build <target> [--dev] [--out PATH] [--force]

    One-shot build pipeline: studio_build_check preflight (skipped
    with --force), then unity_build_player. Auto-generates the
    output path under studio/builds/<date>/<target>/ using
    PlayerSettings.product_name when --out is omitted.

    --dev = development build.
    --force = skip the build_check preflight (use at own risk).
    """
    if not args:
        choices = sorted(set(_BUILD_TARGET_ALIASES.keys()))
        return CommandResult(
            handled=True, ok=False,
            message=(
                f"Usage: /build <target> [--dev] [--out PATH] [--force]   "
                f"Targets: {choices}"
            ),
        )

    target_key = args[0].lower()
    canonical = _BUILD_TARGET_ALIASES.get(target_key)
    if canonical is None:
        return CommandResult(
            handled=True, ok=False,
            message=(
                f"Unknown build target {target_key!r}. "
                f"Choices: {sorted(set(_BUILD_TARGET_ALIASES.keys()))}"
            ),
        )

    dev_build = False
    force = False
    out_override: Optional[str] = None
    i = 1
    while i < len(args):
        a = args[i]
        if a in ("--dev", "-d", "--development"):
            dev_build = True
            i += 1
        elif a in ("--force", "-f"):
            force = True
            i += 1
        elif a in ("--out", "-o") and i + 1 < len(args):
            out_override = args[i + 1]
            i += 2
        else:
            i += 1

    # Validate studio state
    try:
        from ..studio.tools import _STATE, studio_build_check
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio package not importable: {exc}",
        )
    if _STATE is None:
        return CommandResult(
            handled=True, ok=False,
            message="No active studio. Run /init first or `cd` into a Unity project.",
        )

    # Need a Unity bridge for the actual build
    if ctx is None or ctx.unity_bridge is None:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "/build needs a connected Unity bridge. Start chat from a "
                "directory with a Unity project open + the bridge listening "
                "on port 7777."
            ),
        )
    try:
        if not ctx.unity_bridge.connect(timeout=2.0):
            return CommandResult(
                handled=True, ok=False,
                message="Unity bridge not connected. Open Unity Editor + start the bridge.",
            )
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            message=f"Unity bridge connect failed: {exc}",
        )

    # Wire the bridge into BOTH module globals so studio_build_check
    # (which reads studio.tools._UNITY) AND unity_build_player
    # (which reads unity_tools._UNITY) both see it.
    try:
        from ..tools import unity_tools as _ut_mod
        from ..studio.tools import init_studio_unity
        _ut_mod._UNITY = ctx.unity_bridge
        init_studio_unity(ctx.unity_bridge)
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"Tool modules not importable: {exc}",
        )

    # Preflight (unless --force)
    if not force:
        try:
            preflight = studio_build_check()
        except Exception as exc:  # noqa: BLE001
            return CommandResult(
                handled=True, ok=False,
                tool_name="studio_build_check",
                message=f"preflight failed: {exc}",
            )
        if preflight.get("verdict") != "pass":
            blockers = preflight.get("violations") or preflight.get("blockers") or []
            return CommandResult(
                handled=True, ok=False,
                tool_name="studio_build_check",
                tool_result=preflight,
                message=(
                    f"Build preflight FAILED ({len(blockers)} blocker(s)): "
                    f"{', '.join(blockers[:5])}. "
                    "Fix or use /build <target> --force to skip the gate."
                ),
            )

    # Decide output path
    if out_override:
        output_path = out_override
    else:
        # product_name from PlayerSettings; falls back to project name
        product_name = "Game"
        try:
            from ..tools.unity_tools import unity_get_player_settings
            settings = unity_get_player_settings()
            if settings.get("ok"):
                raw_name = (settings.get("product_name") or "").strip()
                # Sanitize for filesystem
                safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in raw_name).strip("_")
                if safe:
                    product_name = safe
        except Exception:  # noqa: BLE001
            pass
        import datetime as _dt
        date_dir = _dt.datetime.now().strftime("%Y-%m-%d")
        ext = _BUILD_EXTENSION.get(canonical, "")
        builds_root = _STATE.paths.root / "builds" / date_dir / canonical
        output_path = str(builds_root / f"{product_name}{ext}")

    # Fire the build. Bridge is already wired (above) so
    # unity_build_player can reach it.
    try:
        from ..tools.unity_tools import unity_build_player
    except ImportError:
        return CommandResult(
            handled=True, ok=False,
            message="unity_build_player tool not registered. Re-run /init.",
        )

    try:
        result = unity_build_player(
            output_path=output_path,
            target=canonical,
            development_build=dev_build,
        )
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="unity_build_player",
            message=f"build failed: {exc}",
        )

    ok = bool(result.get("ok"))
    if ok:
        size_mb = result.get("total_size_bytes", 0) / (1024 * 1024)
        warnings = result.get("total_warnings", 0)
        time_s = result.get("total_time_seconds", 0)
        msg = (
            f"Build SUCCEEDED -- {canonical} -> {output_path} "
            f"({size_mb:.1f} MB, {warnings} warning(s), {time_s:.1f}s)"
        )
    else:
        errs = result.get("total_errors", 0)
        msg = f"Build FAILED -- {canonical}, {errs} error(s): {result.get('error', '?')}"

    return CommandResult(
        handled=True, ok=ok,
        tool_name="unity_build_player",
        tool_result=result,
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


def _resolve_task_partial_id(partial: str) -> tuple[Optional[str], Optional[CommandResult]]:
    """Phase 70 helper: turn a short id (the first 8 chars /next shows)
    into the full task id. Returns (full_id, None) on success or
    (None, error_result) if not found / ambiguous so the caller can
    return the error_result directly.
    """
    if not partial:
        return None, CommandResult(
            handled=True, ok=False,
            message=(
                "Need a task id. Try `/next` first to get one, then "
                "use the short id (first 8 chars) it shows."
            ),
        )
    try:
        from ..studio.tools import studio_find_task
    except ImportError as exc:
        return None, CommandResult(
            handled=True, ok=False,
            message=f"studio_find_task not importable: {exc}",
        )
    try:
        result = studio_find_task(partial)
    except Exception as exc:  # noqa: BLE001
        return None, CommandResult(
            handled=True, ok=False,
            message=f"task lookup failed: {exc}",
        )
    if not result.get("ok"):
        return None, CommandResult(
            handled=True, ok=False,
            message=result.get("error") or "task lookup failed",
        )
    matches = result.get("matches", [])
    if not matches:
        return None, CommandResult(
            handled=True, ok=False,
            message=(
                f"No task id starts with {partial!r}. "
                f"Use /tasks to see the backlog, then copy the short id."
            ),
        )
    if len(matches) > 1:
        # Show top 5 candidates so the operator can disambiguate.
        sample = ", ".join(
            f"{m['id'][:8]} ({m['title'][:32]})"
            for m in matches[:5]
        )
        more = f", +{len(matches) - 5} more" if len(matches) > 5 else ""
        return None, CommandResult(
            handled=True, ok=False,
            message=(
                f"{len(matches)} tasks match {partial!r}: {sample}{more}. "
                f"Add more characters to disambiguate."
            ),
        )
    return matches[0]["id"], None


def _dispatch_task_status(args: list[str], status: str, verb: str) -> CommandResult:
    """Phase 70 shared handler for /take (→in_progress), /done (→done),
    /unblock (→pending). Status is hard-coded by the caller; only the
    task id comes from the user."""
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message=f"Usage: /{verb} <task-id>  (run /next to find one)",
        )
    full_id, err = _resolve_task_partial_id(args[0])
    if err is not None:
        return err
    try:
        from ..studio.tools import studio_update_task_status
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_update_task_status not importable: {exc}",
        )
    try:
        result = studio_update_task_status(full_id, status)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_update_task_status",
            message=f"status update failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_update_task_status",
            tool_result=result,
            message=result.get("error") or "status update failed",
        )
    msg = f"Task {full_id[:8]} → {status}"
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_update_task_status",
        tool_result=result,
        message=msg,
    )


def _dispatch_block(args: list[str]) -> CommandResult:
    """Phase 70: /block <task-id> [reason words...] — flip a task to
    blocked and (optionally) append the reason to its blockers list.
    The reason can be multi-word; we join args[1:] back into one string.
    """
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message="Usage: /block <task-id> [reason]  (run /next to find an id)",
        )
    full_id, err = _resolve_task_partial_id(args[0])
    if err is not None:
        return err
    reason = " ".join(args[1:]).strip()
    try:
        from ..studio.tools import studio_block_task
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_block_task not importable: {exc}",
        )
    try:
        result = studio_block_task(full_id, reason)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_block_task",
            message=f"block failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_block_task",
            tool_result=result,
            message=result.get("error") or "block failed",
        )
    blocker_count = len(result.get("blockers", []))
    msg = f"Task {full_id[:8]} → blocked ({blocker_count} reason{'s' if blocker_count != 1 else ''} on record)"
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_block_task",
        tool_result=result,
        message=msg,
    )


def _dispatch_why(args: list[str]) -> CommandResult:
    """Phase 70: /why <task-id> — explain a task's status and any
    blockers / unsatisfied deps. Read-only diagnostic — never mutates."""
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message="Usage: /why <task-id>",
        )
    full_id, err = _resolve_task_partial_id(args[0])
    if err is not None:
        return err
    try:
        from ..studio.tools import studio_explain_task
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_explain_task not importable: {exc}",
        )
    try:
        result = studio_explain_task(full_id)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_explain_task",
            message=f"why lookup failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_explain_task",
            tool_result=result,
            message=result.get("error") or "why lookup failed",
        )
    # Build a one-line summary explaining the current state.
    parts: list[str] = []
    parts.append(f"'{result['title']}' [{result['role']}] is {result['status']}")
    if result.get("blockers"):
        parts.append(f"{len(result['blockers'])} blocker(s) on record")
    if result.get("unsatisfied_dep_count", 0):
        parts.append(
            f"{result['unsatisfied_dep_count']}/{len(result['depends_on'])} "
            f"deps unsatisfied"
        )
    if result.get("ready_to_start"):
        parts.append("ready to start")
    msg = " — ".join(parts)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_explain_task",
        tool_result=result,
        message=msg,
    )


def _dispatch_show(args: list[str]) -> CommandResult:
    """Phase 86: /show <task-id> — full task content viewer.

    Companion to /why (status diagnostic). Same underlying
    studio_explain_task tool, but the message renders the full
    multi-line body — title + role + status + milestone + every
    blocker + every dep with its status + the description (with
    any /note entries inline). The 'tell me everything about
    this task' command.
    """
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /show <task-id>   "
                "(run /next or /tasks to find an id; /why for status diagnostic)"
            ),
        )
    full_id, err = _resolve_task_partial_id(args[0])
    if err is not None:
        return err
    try:
        from ..studio.tools import studio_explain_task
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_explain_task not importable: {exc}",
        )
    try:
        result = studio_explain_task(full_id)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_explain_task",
            message=f"show failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_explain_task",
            tool_result=result,
            message=result.get("error") or "show failed",
        )

    # Multi-line full-content rendering — different from /why's
    # one-line diagnostic. Chat panels can render the tool_result
    # however they like; the message is the readable transcript form.
    lines: list[str] = []
    lines.append(f"{result['title']}  [{result['role']}]  ({result['status']})")
    lines.append(f"  id: {result['task_id']}")
    if result.get("milestone"):
        lines.append(f"  milestone: {result['milestone']}")
    description = (result.get("description") or "").strip()
    if description:
        lines.append("  description:")
        for descr_line in description.splitlines():
            lines.append(f"    {descr_line}")
    else:
        lines.append("  description: (none — use /note <id> <text> to add one)")
    blockers = result.get("blockers") or []
    if blockers:
        lines.append(f"  blockers ({len(blockers)}):")
        for b in blockers:
            lines.append(f"    - {b}")
    deps = result.get("depends_on") or []
    if deps:
        lines.append(f"  depends_on ({len(deps)}):")
        for d in deps:
            mark = "✓" if d.get("satisfied") else "✗"
            lines.append(
                f"    {mark} {d.get('id', '?')[:8]}  {d.get('title', '')}  "
                f"[{d.get('status', '?')}]"
            )
    if result.get("ready_to_start"):
        lines.append("  ready to start (status=pending, no blockers, deps satisfied)")
    msg = "\n".join(lines)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_explain_task",
        tool_result=result,
        message=msg,
    )


def _dispatch_wrap_up() -> CommandResult:
    """Phase 85: /wrap-up — end-of-day digest pairing with morning
    /standup. Surfaces today's closures + carry-over (in-flight) +
    still-blocked + commit count + journal entry count + next-pending
    suggestion for tomorrow.

    Calendar-day scoped (local midnight cutoff), not 24h sliding —
    so 'today' means today, regardless of when in the day you run it.
    """
    try:
        from ..studio.tools import studio_wrap_up
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_wrap_up not importable: {exc}",
        )
    try:
        result = studio_wrap_up()
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_wrap_up",
            message=f"wrap-up failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_wrap_up",
            tool_result=result,
            message=result.get("error") or "wrap-up failed",
        )

    # Multi-line summary for chat panel rendering
    lines: list[str] = [f"Wrap-up for {result['date']}:"]
    lines.append(
        f"  Closed today: {result['closed_today_count']} task(s)"
    )
    for t in result["closed_today"][:5]:
        lines.append(f"    {t['id'][:8]}  [{t['role']}]  {t['title']}")

    lines.append(
        f"  Carrying over: {result['in_flight_count']} in-flight"
    )
    for t in result["in_flight"][:5]:
        lines.append(f"    {t['id'][:8]}  [{t['role']}]  {t['title']}")

    if result["blocked_count"]:
        lines.append(f"  Still blocked: {result['blocked_count']}")
        for t in result["blocked"][:3]:
            reasons = "; ".join(t["blockers"]) if t["blockers"] else "(no reason)"
            lines.append(
                f"    {t['id'][:8]}  [{t['role']}]  {t['title']}  — {reasons}"
            )

    lines.append(
        f"  Today: {result['commits_today_count']} commit(s), "
        f"{result['journal_entries_today']} journal entr"
        f"{'y' if result['journal_entries_today'] == 1 else 'ies'}"
    )

    nxt = result.get("next_pick")
    if nxt:
        lines.append(
            f"  Tomorrow's next: '{nxt['title']}' "
            f"[{nxt['role']}, id={nxt['id'][:8]}]"
        )
    else:
        lines.append("  Tomorrow's next: nothing pending — backlog is dry.")

    msg = "\n".join(lines)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_wrap_up",
        tool_result=result,
        message=msg,
    )


def _dispatch_discard(args: list[str]) -> CommandResult:
    """Phase 84: /discard <task-id> [reason words...] — set status to
    REJECTED. The 'won't do' close-out for stale pending work.
    Optional reason is appended to the blockers list with a 'rejected:'
    prefix so the rationale stays with the task.

    Use this instead of /block when the task is dead, not stuck.
    /block keeps a task in scope; /discard removes it from scope.
    """
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /discard <task-id> [reason]   "
                "(closes a task as REJECTED — use /block if it's still in scope)"
            ),
        )
    full_id, err = _resolve_task_partial_id(args[0])
    if err is not None:
        return err
    reason = " ".join(args[1:]).strip()
    try:
        from ..studio.tools import studio_reject_task
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_reject_task not importable: {exc}",
        )
    try:
        result = studio_reject_task(full_id, reason)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_reject_task",
            message=f"discard failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_reject_task",
            tool_result=result,
            message=result.get("error") or "discard failed",
        )
    msg = (
        f"Task {full_id[:8]} → rejected"
        + (f" — '{reason}'" if reason else " (no reason recorded)")
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_reject_task",
        tool_result=result,
        message=msg,
    )


def _dispatch_milestone(args: list[str]) -> CommandResult:
    """Phase 84: /milestone <name> | <description> — create a milestone.

    Parallel to /decide: pipe-separator splits the multi-word name
    from a multi-word description. Without a pipe, the whole line is
    the name (description empty). Empty name rejected.
    """
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /milestone <name> | <description>   "
                "(e.g. /milestone Vertical slice | demo-ready by Q3)"
            ),
        )
    line = " ".join(args)
    if "|" in line:
        name_part, _, desc_part = line.partition("|")
        name = name_part.strip()
        description = desc_part.strip()
    else:
        name = line.strip()
        description = ""

    if not name:
        return CommandResult(
            handled=True, ok=False,
            message="milestone name cannot be empty; put text BEFORE the | character",
        )

    try:
        from ..studio.tools import studio_add_milestone
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_add_milestone not importable: {exc}",
        )
    try:
        result = studio_add_milestone(name=name, description=description)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_add_milestone",
            message=f"milestone create failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_add_milestone",
            tool_result=result,
            message=result.get("error") or "milestone create failed",
        )
    msg = (
        f"Created milestone {result['milestone_id'][:8]}: '{name}'"
        + ("" if description else " — no description; consider adding one")
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_add_milestone",
        tool_result=result,
        message=msg,
    )


def _dispatch_blocked() -> CommandResult:
    """Phase 83: /blocked — every blocked task across the studio with
    its full blocker reasons. Producer's 'what do I unblock now?' scan.
    """
    try:
        from ..studio.tools import studio_blocked_tasks
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_blocked_tasks not importable: {exc}",
        )
    try:
        result = studio_blocked_tasks()
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_blocked_tasks",
            message=f"blocked lookup failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_blocked_tasks",
            tool_result=result,
            message=result.get("error") or "blocked lookup failed",
        )

    count = result["count"]
    if count == 0:
        msg = "Nothing blocked — clear runway."
    else:
        lines = [f"{count} blocked task(s):"]
        for t in result["tasks"][:10]:
            reasons = "; ".join(t["blockers"]) if t["blockers"] else "(no reason recorded)"
            lines.append(
                f"  {t['id'][:8]}  [{t['role']}]  {t['title']}  — {reasons}"
            )
        if count > 10:
            lines.append(f"  ... +{count - 10} more")
        msg = "\n".join(lines)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_blocked_tasks",
        tool_result=result,
        message=msg,
    )


def _dispatch_inflight() -> CommandResult:
    """Phase 83: /inflight — every in_progress task with its owner.
    Sorted oldest-first so long-running work bubbles up (those are
    the triage candidates — /why <id> or /block <id> them).
    """
    try:
        from ..studio.tools import studio_inflight_tasks
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_inflight_tasks not importable: {exc}",
        )
    try:
        result = studio_inflight_tasks()
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_inflight_tasks",
            message=f"inflight lookup failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_inflight_tasks",
            tool_result=result,
            message=result.get("error") or "inflight lookup failed",
        )

    count = result["count"]
    if count == 0:
        msg = "Nothing in flight — run /next to pick something up."
    else:
        by_role_str = ", ".join(
            f"{n} {r}" for r, n in sorted(result["by_role"].items())
        )
        lines = [f"{count} in flight ({by_role_str}):"]
        for t in result["tasks"][:10]:
            lines.append(
                f"  {t['id'][:8]}  [{t['role']}]  {t['title']}"
            )
        if count > 10:
            lines.append(f"  ... +{count - 10} more")
        msg = "\n".join(lines)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_inflight_tasks",
        tool_result=result,
        message=msg,
    )


def _dispatch_who(args: list[str]) -> CommandResult:
    """Phase 82: /who <role> — full status drill-down for one role.
    Surfaces every task that role owns, grouped by status, with
    recent done capped to last 7 days so the response stays scannable.
    """
    if not args:
        # No role given → list valid roles so the operator can re-issue.
        try:
            from ..studio.models import ROLES
            roles_list = ", ".join(sorted(ROLES))
        except Exception:
            roles_list = "(unable to load roles)"
        return CommandResult(
            handled=True, ok=False,
            message=f"Usage: /who <role>   Allowed: {roles_list}",
        )
    role = args[0]
    try:
        from ..studio.tools import studio_role_status
        from ..studio.models import ROLES
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_role_status not importable: {exc}",
        )
    if role not in ROLES:
        return CommandResult(
            handled=True, ok=False,
            message=(
                f"Unknown role {role!r}. Try one of: {', '.join(sorted(ROLES))}"
            ),
        )
    try:
        result = studio_role_status(role=role)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_role_status",
            message=f"role status failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_role_status",
            tool_result=result,
            message=result.get("error") or "role status failed",
        )

    # Multi-line summary so the chat panel shows the per-bucket counts
    # plus the actual in_progress + blocked titles (the ones the producer
    # cares about most).
    lines: list[str] = []
    lines.append(
        f"{role}: {result['total']} task(s) total — "
        f"{result['in_progress_count']} in-flight, "
        f"{result['pending_count']} pending, "
        f"{result['blocked_count']} blocked, "
        f"{result['review_count']} review, "
        f"{result['done_recent_count']} done in last 7d "
        f"({result['done_total']} done total)"
    )
    if result["in_progress"]:
        lines.append("  in-flight:")
        for t in result["in_progress"][:5]:
            lines.append(f"    {t['id'][:8]}  {t['title']}")
    if result["blocked"]:
        lines.append("  blocked:")
        for t in result["blocked"][:5]:
            blockers = "; ".join(t["blockers"]) if t["blockers"] else "(no reason)"
            lines.append(f"    {t['id'][:8]}  {t['title']}  — {blockers}")
    msg = "\n".join(lines)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_role_status",
        tool_result=result,
        message=msg,
    )


def _dispatch_recent(args: list[str]) -> CommandResult:
    """Phase 81: /recent [days] — combined activity timeline. Surfaces
    commits + closed tasks + decisions + journal entries from the last
    N days (default 7), DESC by timestamp.

    A producer's 'what happened recently' catch-up. Complements
    /standup (which is forward-looking — what's open today) by being
    backward-looking — what we already shipped + decided + recorded.
    """
    days = 7.0
    if args:
        try:
            days = float(args[0])
        except ValueError:
            return CommandResult(
                handled=True, ok=False,
                message=f"days must be a number; got {args[0]!r}",
            )
        if days <= 0:
            return CommandResult(
                handled=True, ok=False,
                message="days must be positive",
            )
    try:
        from ..studio.tools import studio_recent_activity
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_recent_activity not importable: {exc}",
        )
    try:
        result = studio_recent_activity(days=days)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_recent_activity",
            message=f"recent activity failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_recent_activity",
            tool_result=result,
            message=result.get("error") or "recent activity failed",
        )

    by_src = result.get("by_source", {})
    total = result.get("event_count", 0)
    if total == 0:
        msg = f"Nothing landed in the last {days:g} day(s) — quiet stretch."
    else:
        parts: list[str] = []
        for label in ("commit", "task", "decision", "journal"):
            count = by_src.get(label, 0)
            if count:
                parts.append(f"{count} {label}{'s' if count != 1 else ''}")
        breakdown = ", ".join(parts) if parts else "0 events"
        msg = f"Last {days:g}d: {total} events ({breakdown})"
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_recent_activity",
        tool_result=result,
        message=msg,
    )


def _dispatch_note(args: list[str]) -> CommandResult:
    """Phase 80: /note <task-id> <text words...> — append a timestamped
    note to a task's description. Existing description is preserved;
    the new note is separated by a blank line.

    Uses the Phase 70 partial-id resolver so the operator can pass the
    8-char short id /next prints.
    """
    if len(args) < 2:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /note <task-id> <text>   "
                "(e.g. /note 2ba0e65c wait until URP migration lands)"
            ),
        )
    full_id, err = _resolve_task_partial_id(args[0])
    if err is not None:
        return err
    note = " ".join(args[1:]).strip()
    if not note:
        return CommandResult(
            handled=True, ok=False,
            message="Note text is empty — say what to append.",
        )
    try:
        from ..studio.tools import studio_append_task_note
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_append_task_note not importable: {exc}",
        )
    try:
        result = studio_append_task_note(full_id, note)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_append_task_note",
            message=f"note failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_append_task_note",
            tool_result=result,
            message=result.get("error") or "note failed",
        )
    msg = (
        f"Note appended to {full_id[:8]}: {note[:60]}"
        + ("..." if len(note) > 60 else "")
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_append_task_note",
        tool_result=result,
        message=msg,
    )


def _dispatch_dep(args: list[str]) -> CommandResult:
    """Phase 80: /dep <task-id> <dep-id> — declare that the first task
    depends on the second being DONE first. Both ids are partial-id
    resolved against the backlog.

    The Phase 69 /next command honours this dependency — it will skip
    the dependent task until the dep is done.
    """
    if len(args) < 2:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /dep <task-id> <dep-id>   "
                "(first depends on second being done first)"
            ),
        )
    task_full, err = _resolve_task_partial_id(args[0])
    if err is not None:
        return err
    dep_full, err = _resolve_task_partial_id(args[1])
    if err is not None:
        return err
    try:
        from ..studio.tools import studio_add_task_dependency
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_add_task_dependency not importable: {exc}",
        )
    try:
        result = studio_add_task_dependency(task_full, dep_full)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_add_task_dependency",
            message=f"dep failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_add_task_dependency",
            tool_result=result,
            message=result.get("error") or "dep failed",
        )
    dep_count = len(result.get("depends_on", []))
    msg = (
        f"{task_full[:8]} now depends on {dep_full[:8]} "
        f"({dep_count} dep{'s' if dep_count != 1 else ''} total)"
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_add_task_dependency",
        tool_result=result,
        message=msg,
    )


def _dispatch_commit(args: list[str]) -> CommandResult:
    """Phase 79: /commit <message words...> — stage and commit at the
    studio's git root, then append a journal entry recording the sha.

    Multi-word: every arg word is joined with a space; no quoting
    required. Cleanly distinguishes 'not a git repo', 'nothing to
    commit', and real git failures.

    On success the journal entry reads:
      `commit <sha>: <message>`
    so the daily /journal naturally reflects code-time activity too.
    """
    message = " ".join(args).strip()
    if not message:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /commit <message>   "
                "(e.g. /commit fix boss arena lighting bake)"
            ),
        )
    try:
        from ..studio.tools import studio_commit, studio_journal_append
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_commit not importable: {exc}",
        )
    try:
        result = studio_commit(message)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_commit",
            message=f"commit failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_commit",
            tool_result=result,
            message=result.get("error") or "commit failed",
        )

    # On success, write a journal entry so /journal shows code-time.
    # Don't fail the whole command if journaling itself trips up.
    sha = result.get("sha", "?")
    try:
        studio_journal_append(f"commit {sha}: {message}")
    except Exception:  # noqa: BLE001
        pass  # commit already landed; journaling is best-effort

    msg = f"Committed {sha}: {message[:60]}" + ("..." if len(message) > 60 else "")
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_commit",
        tool_result=result,
        message=msg,
    )


def _dispatch_burndown(args: list[str]) -> CommandResult:
    """Phase 76: /burndown [milestone-id] — ASCII bar chart per
    milestone, showing how close each is to ship. Without an id it
    surfaces every milestone (sorted by ascending completion so the
    farthest-from-shipping ones bubble to the top). With an id, it
    narrows to just that milestone. Always includes a project-wide
    rollup so orphan-task drag is visible.
    """
    milestone_id = args[0] if args else ""
    try:
        from ..studio.tools import studio_burndown
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_burndown not importable: {exc}",
        )
    try:
        result = studio_burndown(milestone_id=milestone_id)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_burndown",
            message=f"burndown failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_burndown",
            tool_result=result,
            message=result.get("error") or "burndown failed",
        )

    project = result["project"]
    milestone_rows = result["milestones"]
    # Multi-line ASCII chart in message line so chat panels render it
    # as-is (monospace).
    lines: list[str] = []
    lines.append(
        f"Project {project['bar']}  "
        f"({project['done_count']}/{project['task_count']} done, "
        f"{project['in_progress_count']} in-flight, "
        f"{project['blocked_count']} blocked)"
    )
    if milestone_rows:
        for row in milestone_rows[:10]:  # cap to avoid wall-of-bars
            lines.append(
                f"  {row['name'][:30]:<30} {row['bar']}  "
                f"({row['done_count']}/{row['task_count']})"
            )
        if len(milestone_rows) > 10:
            lines.append(f"  ... +{len(milestone_rows) - 10} more milestones")
    else:
        lines.append("  No milestones in this studio yet — try /scaffold "
                      "to seed some.")
    msg = "\n".join(lines)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_burndown",
        tool_result=result,
        message=msg,
    )


def _dispatch_find(args: list[str]) -> CommandResult:
    """Phase 75: /find <substring> — search every text surface of the
    studio at once. Joins multi-word args back into a single needle
    so the user doesn't need to quote phrases.

    Returns a structured payload grouped by source (tasks, decisions,
    milestones, docs, journal) plus a flat all_hits list for chat
    panels that want a single ranked stream.
    """
    needle = " ".join(args).strip()
    if not needle:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /find <substring>   "
                "(e.g. /find boss arena, /find URP, /find pickup VFX)"
            ),
        )
    try:
        from ..studio.tools import studio_find
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_find not importable: {exc}",
        )
    try:
        result = studio_find(needle)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_find",
            message=f"find failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_find",
            tool_result=result,
            message=result.get("error") or "find failed",
        )

    total = result.get("total_hits", 0)
    if total == 0:
        msg = f"No hits for {needle!r} across tasks/decisions/docs/journal."
    else:
        # Build a per-bucket breakdown for the one-line summary
        parts: list[str] = []
        for label, key in (("tasks", "tasks"), ("decisions", "decisions"),
                            ("docs", "docs"), ("milestones", "milestones"),
                            ("journal", "journal")):
            count = len(result.get(key, []))
            if count:
                parts.append(f"{count} {label}")
        breakdown = ", ".join(parts) if parts else "0 hits"
        msg = f"{total} hit(s) for {needle!r}: {breakdown}"
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_find",
        tool_result=result,
        message=msg,
    )


def _dispatch_decide(args: list[str]) -> CommandResult:
    """Phase 73: /decide <title> | <summary>   — record a design decision.

    The split delimiter is '|' so titles and summaries can each be
    multi-word without quoting. Falls back to using the whole line as
    the title (no summary) if no pipe is present.

    The decision lands as 'proposed' — same as studio_propose_decision.
    Operators can ratify with the existing studio_ratify_decision tool
    once consensus is reached.
    """
    if not args:
        return CommandResult(
            handled=True, ok=False,
            message=(
                "Usage: /decide <title> | <summary>   "
                "(e.g. /decide use URP | already adopted; SRP migration "
                "later if needed)"
            ),
        )
    line = " ".join(args)
    if "|" in line:
        title_part, _, summary_part = line.partition("|")
        title = title_part.strip()
        summary = summary_part.strip()
    else:
        # No pipe — treat the whole line as the title (no summary).
        title = line.strip()
        summary = ""

    if not title:
        return CommandResult(
            handled=True, ok=False,
            message="title cannot be empty; put text BEFORE the | character",
        )

    try:
        from ..studio.tools import studio_propose_decision
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_propose_decision not importable: {exc}",
        )
    try:
        result = studio_propose_decision(title=title, summary=summary)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_propose_decision",
            message=f"decision propose failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_propose_decision",
            tool_result=result,
            message=result.get("error") or "decision propose failed",
        )
    msg = (
        f"Recorded decision {result['decision_id'][:8]}: '{title}' "
        f"(status: {result.get('status', 'proposed')})"
        + ("" if summary else " — no summary; consider adding one")
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_propose_decision",
        tool_result=result,
        message=msg,
    )


def _dispatch_log(args: list[str]) -> CommandResult:
    """Phase 72: /log <message words...> — append a timestamped entry
    to today's studio/memory/journal/<YYYY-MM-DD>.md. Multi-word
    messages are joined with spaces; no quoting required."""
    message = " ".join(args).strip()
    if not message:
        return CommandResult(
            handled=True, ok=False,
            message="Usage: /log <your note>  (e.g. /log boss arena lit, ready for QA)",
        )
    try:
        from ..studio.tools import studio_journal_append
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_journal_append not importable: {exc}",
        )
    try:
        result = studio_journal_append(message)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_journal_append",
            message=f"log failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_journal_append",
            tool_result=result,
            message=result.get("error") or "log failed",
        )
    msg = (
        f"Logged at {result['timestamp']} "
        f"({result['date']}): {message[:60]}"
        + ("..." if len(message) > 60 else "")
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_journal_append",
        tool_result=result,
        message=msg,
    )


def _dispatch_journal(args: list[str]) -> CommandResult:
    """Phase 72: /journal [days] — read the last N days of journal
    entries (default 1 = today only). Returns content per-day plus
    a flat 'recent' list."""
    days = 1
    if args:
        try:
            days = int(args[0])
        except ValueError:
            return CommandResult(
                handled=True, ok=False,
                message=f"days must be an integer; got {args[0]!r}",
            )
        if days <= 0:
            return CommandResult(
                handled=True, ok=False,
                message="days must be positive",
            )
    try:
        from ..studio.tools import studio_journal_read
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_journal_read not importable: {exc}",
        )
    try:
        result = studio_journal_read(days=days)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_journal_read",
            message=f"journal read failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_journal_read",
            tool_result=result,
            message=result.get("error") or "journal read failed",
        )

    total_days = result.get("total_days", 0)
    if total_days == 0:
        msg = (
            f"No journal entries in the last {days} day"
            f"{'s' if days != 1 else ''} — drop one with /log <message>."
        )
    else:
        # Show the most recent day's content preview as the message line
        most_recent = result["recent"][0]
        preview_lines = [
            ln for ln in most_recent["content"].splitlines() if ln.strip()
        ][:6]
        preview = "\n".join(preview_lines)
        msg = f"{total_days} day(s) with entries (most recent: {most_recent['date']})\n{preview}"
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_journal_read",
        tool_result=result,
        message=msg,
    )


def _dispatch_standup(args: list[str]) -> CommandResult:
    """Phase 71: /standup [hours] — morning digest of what changed and
    what's open. Default window: 24h. Returns a one-line message
    summarising the four key numbers (closed / in-flight / blocked /
    pending) plus structured detail in tool_result for richer rendering.
    """
    window_hours = 24.0
    if args:
        try:
            window_hours = float(args[0])
        except ValueError:
            return CommandResult(
                handled=True, ok=False,
                message=f"window must be a number of hours; got {args[0]!r}",
            )
        if window_hours <= 0:
            return CommandResult(
                handled=True, ok=False,
                message="window hours must be positive",
            )

    try:
        from ..studio.tools import studio_standup
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_standup not importable: {exc}",
        )
    try:
        result = studio_standup(window_hours=window_hours)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_standup",
            message=f"standup failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_standup",
            tool_result=result,
            message=result.get("error") or "standup failed",
        )

    msg = (
        f"Last {window_hours:g}h: "
        f"closed {result['closed_recent_count']}, "
        f"in-flight {result['in_flight_count']}, "
        f"blocked {result['blocked_count']}, "
        f"pending {result['pending_count']}"
        + (f", review {result['review_count']}" if result.get("review_count") else "")
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_standup",
        tool_result=result,
        message=msg,
    )


def _dispatch_sprint() -> CommandResult:
    """Phase 69: /sprint — read studio/sprint_current.md, surface the
    plan for today's stand-up.

    Editor users get the same content the LLM would when calling
    studio_read_sprint, but as a one-shot deterministic dispatch.
    """
    try:
        from ..studio.tools import studio_read_sprint
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_read_sprint not importable: {exc}",
        )
    try:
        result = studio_read_sprint()
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_read_sprint",
            message=f"sprint read failed: {exc}",
        )
    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_read_sprint",
            tool_result=result,
            message=result.get("error") or "sprint read failed",
        )
    content = (result.get("content") or "").strip()
    if not content:
        msg = "Sprint plan is empty — drop a quick note in studio/sprint_current.md."
    else:
        # First non-empty line is the human-readable summary; show up
        # to ~10 lines for the message line so the chat panel can render
        # a useful glance without dumping the whole file.
        preview_lines = [
            ln for ln in content.splitlines()[:10] if ln.strip()
        ]
        msg = "\n".join(preview_lines)
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_read_sprint",
        tool_result=result,
        message=msg,
    )


def _dispatch_next(args: list[str]) -> CommandResult:
    """Phase 69: /next [role] — find the next pending task ready to be
    picked up. Optional role filter narrows by discipline.

    A producer's daily move: open chat, `/next`, work on that task.
    No 'list backlog, eyeball priorities, pick something' mental load.
    """
    try:
        from ..studio.tools import studio_next_task
        from ..studio.models import ROLES
    except ImportError as exc:
        return CommandResult(
            handled=True, ok=False,
            message=f"studio_next_task not importable: {exc}",
        )

    role = args[0] if args else ""
    if role and role not in ROLES:
        return CommandResult(
            handled=True, ok=False,
            message=(
                f"Unknown role {role!r}. Try one of: {', '.join(sorted(ROLES))}, "
                f"or omit the role to get the next task across all disciplines."
            ),
        )

    try:
        result = studio_next_task(role=role)
    except Exception as exc:  # noqa: BLE001
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_next_task",
            message=f"next task lookup failed: {exc}",
        )

    if not result.get("ok"):
        return CommandResult(
            handled=True, ok=False,
            tool_name="studio_next_task",
            tool_result=result,
            message=result.get("error") or "next task lookup failed",
        )

    nxt = result.get("task")
    if nxt is None:
        reason = result.get("reason") or "no ready task"
        msg = (
            f"No task ready to pick up — {reason}"
            + (f" (role filter: {role})" if role else "")
        )
        return CommandResult(
            handled=True, ok=True,
            tool_name="studio_next_task",
            tool_result=result,
            message=msg,
        )

    msg = (
        f"Next up: '{nxt['title']}' "
        f"[{nxt['role']}, id={nxt['id'][:8]}"
        + (f", milestone={nxt['milestone']}" if nxt.get("milestone") else "")
        + f"] — {result.get('ready_count', 0)} ready / "
        f"{result.get('pending_count', 0)} pending"
    )
    return CommandResult(
        handled=True, ok=True,
        tool_name="studio_next_task",
        tool_result=result,
        message=msg,
    )


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
