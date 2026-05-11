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


def _init_studio_for_chat(unity: UnityBridge) -> tuple[bool, str]:
    """Wire the studio + every engine tool module into the global
    @tool registry so the LLM can call them from chat. Returns
    (studio_active, summary_line)."""
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

    # 2. Look for a studio/ scaffold near the cwd. If found, wire
    #    init_studio_tools + init_studio_unity so studio_* calls work.
    try:
        from ..studio import StudioPaths, StudioState, init_studio_tools, init_studio_unity
    except ImportError:
        return False, "studio package not importable"

    project_root = _discover_studio_root()
    if project_root is None:
        # Still useful: wire the bridge so non-studio unity_* tools work.
        try:
            init_studio_unity(unity)
        except Exception:
            pass
        return False, "no studio/ found in cwd or its parents"

    try:
        paths = StudioPaths(project_root=project_root)
        state = StudioState(paths)
        init_studio_tools(state)
        init_studio_unity(unity)
        return True, str(project_root)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to init studio for chat")
        return False, f"init failed: {exc}"


def run_chat(config: Config, blender: BlenderBridge, unity: UnityBridge) -> int:
    studio_active, studio_info = _init_studio_for_chat(unity)
    orch = Orchestrator(config)
    session: PromptSession = PromptSession(history=InMemoryHistory())

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
            cmd_result = _handle_slash(user_in, orch, blender, unity)
            if cmd_result == "quit":
                return 0
            continue

        _send_to_llm(orch, user_in)


def _handle_slash(line: str, orch: Orchestrator, blender: BlenderBridge, unity: UnityBridge) -> str | None:
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
                "[cyan]/quit[/cyan]                  exit\n\n"
                "[bold]Studio actions[/bold] (deterministic, bypass LLM)\n"
                "[cyan]/scaffold[/cyan] <genre> [name]   scaffold collectathon/shooter/runner/platformer\n"
                "[cyan]/dashboard[/cyan] [--save] [days]  operator's morning glance\n"
                "[cyan]/ship[/cyan]                    ship readiness check (go/no-go)\n"
                "[cyan]/cost[/cyan] [days]             LLM token + USD spend (default 7d)\n"
                "[cyan]/audit[/cyan] <kind>            kind: lighting/atmosphere/vfx/build/consistency/balance/ship/localization\n"
                "[cyan]/tasks[/cyan] [status]          list backlog tasks, optionally filtered\n"
                "[cyan]/milestones[/cyan]              list milestones\n"
                "[cyan]/decisions[/cyan]               list decisions\n\n"
                "[dim]Any non-slash message goes to the LLM with all 199 tools available.[/dim]\n"
                "[dim]Try: 'scaffold a platformer called Hop Quest' or '/scaffold platformer Hop Quest'.[/dim]",
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
    cmd_result = chat_commands.dispatch(line[1:])
    if cmd_result.handled:
        if cmd_result.quit:
            console.print(f"[dim]{cmd_result.message}[/dim]")
            return "quit"
        marker = "[green][OK][/green]" if cmd_result.ok else "[red][ERR][/red]"
        if cmd_result.tool_name:
            console.print(f"  [dim]-> tool:[/dim] [yellow]{cmd_result.tool_name}[/yellow]")
        console.print(f"  {marker} {cmd_result.message}")
        return None

    console.print(f"[red]Unknown command: /{cmd}[/red]")
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
