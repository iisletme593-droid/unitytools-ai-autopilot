"""Interactive terminal chat REPL for UnityTools.

Phase 56: the REPL is studio-aware by default. On launch it:
- Auto-discovers a studio/ directory in the current working tree
  and calls init_studio_tools(state) so studio_* tools work.
- Calls init_studio_unity(unity) so studio_capture_screenshot +
  studio_unity_attach_audio_source + every engine-gated studio
  tool can reach the bridge.
- Eagerly imports unitytools.tools.* so the @tool registry has
  every Unity / Blender wrapper available to the LLM.
Without these, the LLM could SEE studio_* tools but every call
would error with 'state not initialized'. With them, the chat is
the right way to drive the studio: 'scaffold a collectathon' or
'run ship readiness check' just works.
"""
from __future__ import annotations

import logging
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ..bridges import BlenderBridge, UnityBridge
from ..core.config import Config
from ..core.orchestrator import Orchestrator
from ..core.tool_registry import get_all_tools
from . import chat_commands

logger = logging.getLogger(__name__)
console = Console()

PROMPT_STYLE = Style.from_dict({"prompt": "ansicyan bold"})


def _discover_studio_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` (default: cwd) looking for a sibling
    'studio/' directory with a known doc file. Returns the studio
    directory's parent (the project root) or None."""
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        studio_dir = candidate / "studio"
        if not studio_dir.is_dir():
            continue
        # Sniff for at least one of the canonical scaffolded files —
        # avoids matching a random 'studio' folder unrelated to us.
        markers = ("gdd.md", "backlog.json", "decisions.jsonl",
                    "art_bible.md", "sprint_current.md")
        if any((studio_dir / m).exists() for m in markers):
            return candidate
    return None


def _discover_unity_project_root(start: Path | None = None) -> Path | None:
    """Walk up from `start` looking for a Unity project root —
    a directory containing both `Assets/` and `ProjectSettings/`.
    Returns the project root, or None if we never find one.

    These two folders are Unity's contract: every Unity project on
    disk has them. Matching both (not just Assets/) means we never
    confuse a random folder named 'Assets' with a real project.
    """
    cur = (start or Path.cwd()).resolve()
    for candidate in [cur, *cur.parents]:
        assets = candidate / "Assets"
        settings = candidate / "ProjectSettings"
        if assets.is_dir() and settings.is_dir():
            return candidate
    return None


def _auto_scaffold_studio(project_root: Path) -> tuple[bool, str]:
    """Phase 62: create studio/ + drop starter docs without
    confirmation. Used when the operator opens chat inside a Unity
    project that doesn't have a studio yet — zero-friction onboarding.

    Returns (created, summary).
    """
    try:
        from ..studio import StudioPaths, StudioState
        from ..studio.templates import starter_files
    except ImportError as exc:
        return False, f"studio package not importable: {exc}"

    paths = StudioPaths(project_root=project_root)
    if paths.exists():
        # Race / pre-existing studio — caller should have detected
        # this via _discover_studio_root, but be defensive.
        return False, "already exists"

    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    files_written: list[str] = []
    for rel_path, content in starter_files().items():
        target = paths.root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(content, encoding="utf-8")
            files_written.append(rel_path)
    state = StudioState(paths)
    state.save_tasks([])
    state.save_milestones([])
    return True, str(paths.root)


def _init_studio_for_chat(
    unity: UnityBridge,
    auto_scaffold: bool = True,
    auto_sync: bool = True,
) -> tuple[bool, str]:
    """Wire the studio + every engine tool module into the global
    @tool registry so the LLM can call them from chat. Returns
    (studio_active, summary_line).

    Phase 62: when no studio is discoverable AND cwd looks like a
    Unity project (Assets/ + ProjectSettings/), auto-scaffold one
    rather than making the user run /init manually. Caller can
    pass auto_scaffold=False to opt out (CLI flag --no-auto-init).
    """
    # 1. Eagerly import all the engine + asset modules so their @tool
    #    decorators populate the registry. Each import is a side
    #    effect; missing optional modules are tolerated silently.
    for mod in (
        "unitytools.tools",
        "unitytools.tools.unity_tools",
        "unitytools.tools.asset_tools",
        "unitytools.tools.snapshot_tools",
        "unitytools.tools.scene_intelligence_tools",
        "unitytools.tools.procedural_tools",
        "unitytools.tools.autopilot_quality_tools",
    ):
        try:
            __import__(mod)
        except ImportError:
            pass

    # 2. Look for a studio/ scaffold near the cwd.
    try:
        from ..studio import StudioPaths, StudioState, init_studio_tools, init_studio_unity
    except ImportError:
        return False, "studio package not importable"

    project_root = _discover_studio_root()

    # Phase 62: if no studio exists, AND we're in a Unity project,
    # AND the user didn't opt out, scaffold one automatically.
    auto_created = False
    if project_root is None and auto_scaffold:
        unity_root = _discover_unity_project_root()
        if unity_root is not None:
            created, info = _auto_scaffold_studio(unity_root)
            if created:
                project_root = unity_root
                auto_created = True
                logger.info("Phase 62 auto-scaffold: studio created at %s", info)

    if project_root is None:
        # Still useful: wire the bridge so non-studio unity_* tools work.
        try:
            init_studio_unity(unity)
        except Exception:
            pass
        return False, "no studio/ found and cwd isn't a Unity project (run /init or cd into a Unity project)"

    try:
        paths = StudioPaths(project_root=project_root)
        state = StudioState(paths)
        init_studio_tools(state)
        init_studio_unity(unity)
        # Phase 63: auto-sync. Migrate any older studio (missing
        # docs / dirs introduced by later phases) up to current
        # schema. Never overwrites existing files. Phase 65 added
        # the auto_sync=False opt-out.
        sync_suffix = ""
        if not auto_created and auto_sync:
            try:
                from ..studio.tools import studio_sync
                sync_result = studio_sync(check_only=False)
                applied = sync_result.get("actions_applied", [])
                if applied:
                    sync_suffix = f" (+{len(applied)} schema migrations)"
                    logger.info("Phase 63 auto-sync: %d step(s) applied",
                                 len(applied))
            except Exception:  # noqa: BLE001
                logger.exception("auto-sync failed (non-fatal)")
        suffix = " (auto-scaffolded)" if auto_created else sync_suffix
        return True, f"{project_root}{suffix}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to init studio for chat")
        return False, f"init failed: {exc}"


def run_chat(
    config: Config,
    blender: BlenderBridge,
    unity: UnityBridge,
    auto_scaffold: bool = True,
    auto_sync: bool = True,
) -> int:
    studio_active, studio_info = _init_studio_for_chat(
        unity, auto_scaffold=auto_scaffold, auto_sync=auto_sync,
    )
    orch = Orchestrator(config)
    session: PromptSession = PromptSession(history=InMemoryHistory())

    # Phase 61: context for /dispatch (and any future slash command
    # that needs a real LLM client + bridge).
    dispatch_ctx = chat_commands.DispatchContext(config=config, unity_bridge=unity)

    _print_welcome(config, blender, unity, studio_active, studio_info)

    while True:
        try:
            user_in = session.prompt(
                [("class:prompt", "> ")],
                style=PROMPT_STYLE,
                multiline=False,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting...[/dim]")
            return 0

        if not user_in:
            continue

        if user_in.startswith("/"):
            cmd_result = _handle_slash(user_in, orch, blender, unity, dispatch_ctx)
            if cmd_result == "quit":
                return 0
            continue

        _send_to_llm(orch, user_in)


def _handle_slash(
    line: str,
    orch: Orchestrator,
    blender: BlenderBridge,
    unity: UnityBridge,
    dispatch_ctx: "chat_commands.DispatchContext | None" = None,
) -> str | None:
    parts = line[1:].split()
    if not parts:
        return None
    cmd = parts[0].lower()

    if cmd in ("quit", "exit", "q"):
        console.print("[dim]Goodbye.[/dim]")
        return "quit"

    if cmd == "help":
        console.print(
            Panel(
                "[bold]Meta[/bold]\n"
                "[cyan]/help[/cyan]                  show this help\n"
                "[cyan]/clear[/cyan]                 clear chat history\n"
                "[cyan]/tools[/cyan] [filter]        list registered tools\n"
                "[cyan]/status[/cyan]                show bridge status\n"
                "[cyan]/studio[/cyan]                show active studio summary\n"
                "[cyan]/diag[/cyan]                  one-line diagnostics (tools / roles / behaviours)\n"
                "[cyan]/quit[/cyan]                  exit\n\n"
                "[bold]Studio actions[/bold]\n"
                "[cyan]/init[/cyan] [path]            scaffold a fresh studio/ at cwd or path\n"
                "[cyan]/sync[/cyan] [--check]          bring older studio up to current schema (auto-runs on chat start)\n"
                "[cyan]/scaffold[/cyan] <genre> [name]   collectathon/shooter/runner/platformer\n"
                "[cyan]/dispatch[/cyan] [N] [--dry-run]   run N pending tasks through their roles (autopilot)\n"
                "[cyan]/role[/cyan] <role-id> [brief]    run ONE role one-shot (e.g. /role designer 'Draft GDD')\n"
                "[cyan]/build[/cyan] <target> [--dev]      windows/mac/linux/webgl/android/ios; auto-runs ship preflight first\n"
                "[cyan]/sprint[/cyan]                   read studio/sprint_current.md\n"
                "[cyan]/next[/cyan] [role]              next ready pending task (FIFO, deps respected)\n"
                "[cyan]/take[/cyan] <id>                mark task in_progress\n"
                "[cyan]/done[/cyan] <id>                mark task done\n"
                "[cyan]/block[/cyan] <id> [reason]      mark task blocked + record reason\n"
                "[cyan]/unblock[/cyan] <id>             blocked -> pending\n"
                "[cyan]/why[/cyan] <id>                 explain a task's status + unsatisfied deps\n"
                "[cyan]/note[/cyan] <id> <text>         append a timestamped note to a task's description\n"
                "[cyan]/dep[/cyan] <id> <dep-id>        wire a dependency (first needs second done first)\n"
                "[cyan]/discard[/cyan] <id> [reason]    close task as REJECTED (won't do)\n"
                "[cyan]/milestone[/cyan] <name> | <desc>  create a milestone\n"
                "[cyan]/standup[/cyan] [hours]           daily digest: closed/in-flight/blocked/pending\n"
                "[cyan]/wrap-up[/cyan]                   end-of-day digest (closures + carry-over + tomorrow's next)\n"
                "[cyan]/recent[/cyan] [days]             combined activity timeline (commits+tasks+decisions+journal)\n"
                "[cyan]/who[/cyan] <role>                per-role drill-down (in-flight/pending/blocked/done)\n"
                "[cyan]/blocked[/cyan]                  every blocked task across the studio + reasons\n"
                "[cyan]/inflight[/cyan]                 every in_progress task with owner (oldest-first)\n"
                "[cyan]/log[/cyan] <message>             append a timestamped note to today's journal\n"
                "[cyan]/journal[/cyan] [days]            read last N days of journal entries\n"
                "[cyan]/decide[/cyan] <title> | <summary>  record a design decision (proposed)\n"
                "[cyan]/find[/cyan] <substring>          search tasks/decisions/docs/journal at once\n"
                "[cyan]/burndown[/cyan] [milestone-id]    ASCII bar chart per milestone (+ project rollup)\n"
                "[cyan]/commit[/cyan] <message>          git add -A + commit + journal entry\n"
                "[cyan]/dashboard[/cyan] [--save] [days]  operator's morning glance\n"
                "[cyan]/ship[/cyan]                    ship readiness check (go/no-go)\n"
                "[cyan]/cost[/cyan] [days]             LLM token + USD spend (default 7d)\n"
                "[cyan]/audit[/cyan] <kind>            lighting/atmosphere/vfx/build/consistency/balance/ship/localization\n\n"
                "[bold]Inventory[/bold]\n"
                "[cyan]/tasks[/cyan] [status]          list backlog tasks\n"
                "[cyan]/milestones[/cyan] | /ms        list milestones\n"
                "[cyan]/decisions[/cyan]               list decisions\n"
                "[cyan]/refs[/cyan]                    list reference images\n"
                "[cyan]/screenshots[/cyan] | /shots    list captured screenshots\n"
                "[cyan]/locales[/cyan]                 list string tables\n"
                "[cyan]/dialogs[/cyan]                 list dialog files\n"
                "[cyan]/assets[/cyan]                  asset manifest (all 5 buckets)\n"
                "[cyan]/behaviours[/cyan] [filter]     list Behaviour Library (motion/UI/combat/...)\n"
                "[cyan]/roles[/cyan]                   list all 24 studio roles\n\n"
                "[dim]Any non-slash message routes to gemma4 with all 199 tools available.[/dim]\n"
                "[dim]Try: '/scaffold platformer Hop Quest' or 'scaffold a platformer called Hop Quest'.[/dim]\n\n"
                "[bold]Türkçe alias'ler[/bold] [dim](her komut Türkçe veya İngilizce yazılabilir)[/dim]\n"
                "[dim]/yardım=/help  /durum=/status  /sağlık=/diag  /çıkış=/quit\n"
                "/başlat=/init  /eşitle=/sync  /oluştur=/scaffold  /yürüt=/dispatch  /rol=/role\n"
                "/rapor=/dashboard  /satış=/ship  /maliyet=/cost  /denetim=/audit  /yapı=/build\n"
                "/görev=/tasks  /hedef=/milestones  /referans=/refs  /dil=/locales\n"
                "/diyalog=/dialogs  /varlık=/assets  /davranış=/behaviours  /roller=/roles[/dim]",
                title="Commands",
                border_style="cyan",
            )
        )
        return None

    if cmd == "clear":
        orch.reset()
        console.print("[green][OK] History cleared.[/green]")
        return None

    if cmd == "tools":
        # Optional substring filter so the user can prune the wall:
        # /tools studio   -> only studio_* tools
        # /tools scaffold -> only the scaffolders
        needle = " ".join(parts[1:]).strip().lower()
        rows = [
            spec for spec in get_all_tools()
            if not needle or needle in spec.name.lower()
            or needle in spec.description.lower()
        ]
        title = "Registered Tools" + (f" matching '{needle}'" if needle else "")
        table = Table(title=title, show_lines=False)
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        for spec in rows:
            table.add_row(spec.name, spec.description)
        console.print(table)
        console.print(f"[dim]{len(rows)} of {len(get_all_tools())} tools shown.[/dim]")
        return None

    if cmd == "status":
        console.print(f"  Blender: {'[OK]' if blender.is_available() else '[ERR]'}")
        console.print(f"  Unity:   {'[OK] connected' if unity.connect(timeout=1.0) else '[WAIT] Editor offline'}")
        return None

    if cmd == "studio":
        # Show what the LLM can see about the active studio.
        try:
            from ..studio.tools import studio_get_summary
            summary = studio_get_summary()
            if not summary.get("ok"):
                console.print(f"[yellow]Studio inactive:[/yellow] {summary.get('error', '')}")
                console.print("[dim]Run `unitytools studio-init` in your project root, "
                              "then `/clear` + restart this chat.[/dim]")
                return None
            console.print(
                Panel(
                    f"Root: [cyan]{summary.get('studio_root', '?')}[/cyan]\n"
                    f"GDD: {'OK' if summary.get('has_gdd') else 'missing'}   "
                    f"Art Bible: {'OK' if summary.get('has_art_bible') else 'missing'}   "
                    f"Sprint: {'OK' if summary.get('has_sprint') else 'missing'}\n"
                    f"Tasks: [cyan]{summary.get('task_count', 0)}[/cyan]   "
                    f"Milestones: [cyan]{summary.get('milestone_count', 0)}[/cyan]   "
                    f"Decisions: [cyan]{summary.get('decision_count', 0)}[/cyan]",
                    title="Studio status",
                    border_style="cyan",
                )
            )
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]/studio failed:[/red] {exc}")
        return None

    # Phase 59: route to the deterministic command dispatcher
    # (scaffold / dashboard / ship / cost / audit / tasks / ...).
    # Unknown commands fall through to the error message.
    cmd_result = chat_commands.dispatch(line[1:], ctx=dispatch_ctx)
    if cmd_result.handled:
        if cmd_result.quit:
            console.print(f"[dim]{cmd_result.message}[/dim]")
            return "quit"
        marker = "[green][OK][/green]" if cmd_result.ok else "[red][ERR][/red]"
        if cmd_result.tool_name:
            console.print(f"  [dim]-> tool:[/dim] [yellow]{cmd_result.tool_name}[/yellow]")
        console.print(f"  {marker} {cmd_result.message}")
        return None

    # Phase 78: surface typo suggestions so /buldown → 'did you mean /burndown?'
    suggestions = chat_commands.suggest_command(cmd)
    if suggestions:
        suggest_str = ", ".join(f"/{s}" for s in suggestions)
        console.print(
            f"[red]Unknown command:[/red] /{cmd}  "
            f"[dim]Did you mean: {suggest_str}?[/dim]"
        )
    else:
        console.print(
            f"[red]Unknown command:[/red] /{cmd}  "
            f"[dim](type /help for the full list)[/dim]"
        )
    return None


def _send_to_llm(orch: Orchestrator, message: str) -> None:
    def on_tool_call(name: str, params: dict) -> None:
        params_short = ", ".join(f"{k}={v!r}" for k, v in list(params.items())[:3])
        if len(params) > 3:
            params_short += ", ..."
        console.print(f"  [dim]-> tool:[/dim] [yellow]{name}[/yellow]({params_short})")

    def on_tool_result(name: str, result) -> None:
        ok = isinstance(result, dict) and result.get("ok", True)
        marker = "[green][OK][/green]" if ok else "[red][ERR][/red]"
        console.print(f"  [dim]<- {marker} {name}[/dim]")

    with console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
        try:
            result = orch.chat(message, on_tool_call=on_tool_call, on_tool_result=on_tool_result)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            return

    if result.text:
        console.print(Panel(Markdown(result.text), border_style="green", title="UnityTools AI"))
    if result.stop_reason == "max_iterations":
        console.print("[yellow]Warning: max iteration limit reached.[/yellow]")


def _print_welcome(
    config: Config,
    blender: BlenderBridge,
    unity: UnityBridge,
    studio_active: bool = False,
    studio_info: str = "",
) -> None:
    blender_ok = "[OK]" if blender.is_available() else "[ERR]"
    unity_ok = "[OK] connected" if unity.connect(timeout=1.0) else "[WAIT] offline"
    model_label = config.ollama_model if config.provider == "ollama" else config.model
    studio_line = (
        f"Studio: [green][OK][/green] {studio_info}"
        if studio_active
        else f"Studio: [yellow]inactive[/yellow] ({studio_info})"
    )
    tool_count = len(get_all_tools())
    hint = (
        "Try: 'scaffold a collectathon called Coin Hunter', "
        "'run ship readiness check', 'show recent regressions'."
        if studio_active
        else "Studio tools won't work until a studio/ folder is "
        "discoverable. Run `unitytools studio-init` first."
    )
    console.print(
        Panel(
            f"[bold]UnityTools Chat[/bold]\n"
            f"Provider: [cyan]{config.provider}[/cyan]   "
            f"Model: [cyan]{model_label}[/cyan]\n"
            f"Blender: [cyan]{blender_ok}[/cyan]   "
            f"Unity: [cyan]{unity_ok}[/cyan]   "
            f"{studio_line}\n"
            f"Tools registered: [cyan]{tool_count}[/cyan]\n\n"
            f"[dim]{hint}[/dim]\n"
            f"[dim]Type /help for commands, /quit to exit.[/dim]",
            border_style="cyan",
        )
    )
