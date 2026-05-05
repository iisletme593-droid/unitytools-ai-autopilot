"""Interactive terminal chat REPL for UnityTools."""
from __future__ import annotations

import logging

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

logger = logging.getLogger(__name__)
console = Console()

PROMPT_STYLE = Style.from_dict({"prompt": "ansicyan bold"})


def run_chat(config: Config, blender: BlenderBridge, unity: UnityBridge) -> int:
    orch = Orchestrator(config)
    session: PromptSession = PromptSession(history=InMemoryHistory())

    _print_welcome(config, blender, unity)

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
                "[cyan]/help[/cyan]    show this help\n"
                "[cyan]/clear[/cyan]   clear chat history\n"
                "[cyan]/tools[/cyan]   list registered tools\n"
                "[cyan]/status[/cyan]  show bridge status\n"
                "[cyan]/quit[/cyan]    exit\n\n"
                "[dim]Any non-slash message goes to the selected AI provider.[/dim]",
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
        table = Table(title="Registered Tools", show_lines=False)
        table.add_column("Name", style="cyan")
        table.add_column("Description")
        for spec in get_all_tools():
            table.add_row(spec.name, spec.description)
        console.print(table)
        return None

    if cmd == "status":
        console.print(f"  Blender: {'[OK]' if blender.is_available() else '[ERR]'}")
        console.print(f"  Unity:   {'[OK] connected' if unity.connect(timeout=1.0) else '[WAIT] Editor offline'}")
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


def _print_welcome(config: Config, blender: BlenderBridge, unity: UnityBridge) -> None:
    blender_ok = "[OK]" if blender.is_available() else "[ERR]"
    unity_ok = "[OK] connected" if unity.connect(timeout=1.0) else "[WAIT] offline"
    model_label = config.ollama_model if config.provider == "ollama" else config.model
    console.print(
        Panel(
            f"[bold]UnityTools Chat[/bold]\n"
            f"Provider: [cyan]{config.provider}[/cyan]   "
            f"Model: [cyan]{model_label}[/cyan]   "
            f"Blender: [cyan]{blender_ok}[/cyan]   "
            f"Unity: [cyan]{unity_ok}[/cyan]\n\n"
            f"[dim]Type /help for commands, /quit to exit.[/dim]",
            border_style="cyan",
        )
    )
