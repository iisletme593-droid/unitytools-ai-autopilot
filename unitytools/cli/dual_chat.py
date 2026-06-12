"""Dual-agent interactive chat REPL.

Reader and Worker default to qwen2.5:14b-instruct for fast scene/context work.
Master defaults to qwen3.6:latest for planning when installed.
"""
from __future__ import annotations

import logging
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from ..core.config import Config
from ..core.dual_agent import DualAgentOrchestrator

logger = logging.getLogger(__name__)
console = Console()


def run_dual_chat(
    config: Config,
    master_model: str = "qwen3.6:latest",
    worker_model: str = "qwen2.5:14b-instruct",
    reader_model: str = "qwen2.5:14b-instruct",
) -> int:
    """Run dual-agent interactive chat."""
    console.print(
        Panel.fit(
            "[bold cyan]UnityTools Dual-Agent Chat[/bold cyan]\n"
            f"[dim]Reader:[/dim] {reader_model} [dim](fast scene/context scan)[/dim]\n"
            f"[dim]Master:[/dim] {master_model} [dim](planner)[/dim]\n"
            f"[dim]Worker:[/dim] {worker_model} [dim](executor, fast)[/dim]\n"
            "[bold yellow]Use dual-agent for complex scenes; single-agent is faster for quick edits.[/bold yellow]\n"
            "[dim]Type 'exit' or 'quit' to stop, 'reset' to clear history[/dim]",
            border_style="cyan",
        )
    )

    dual = DualAgentOrchestrator(config, master_model, worker_model, reader_model=reader_model)
    session: PromptSession = PromptSession(history=InMemoryHistory())

    def on_master_thinking(msg: str) -> None:
        console.print(f"[bold magenta]🧠 Master:[/bold magenta] [dim]{msg}[/dim]")

    def on_worker_executing(msg: str) -> None:
        console.print(f"[bold blue]⚙️  Worker:[/bold blue] [dim]{msg}[/dim]")

    def on_tool_call(name: str, params: dict) -> None:
        console.print(f"[yellow]🔧 Tool:[/yellow] {name}")
        if params:
            syntax = Syntax(
                str(params),
                "python",
                theme="monokai",
                line_numbers=False,
                word_wrap=True,
            )
            console.print(syntax)

    def on_tool_result(name: str, result: Any) -> None:
        if isinstance(result, dict):
            ok = result.get("ok", True)
            if ok:
                console.print(f"[green]✓ {name} succeeded[/green]")
            else:
                error = result.get("error", "Unknown error")
                console.print(f"[red]✗ {name} failed: {error}[/red]")
        else:
            console.print(f"[green]✓ {name} completed[/green]")

    while True:
        try:
            user_input = session.prompt("\n[You] > ", multiline=False)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Exiting...[/yellow]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            console.print("[yellow]Goodbye![/yellow]")
            break

        if user_input.lower() == "reset":
            dual.reset()
            console.print("[green]History cleared.[/green]")
            continue

        # Execute with dual-agent
        try:
            result = dual.chat(
                user_input,
                on_master_thinking=on_master_thinking,
                on_worker_executing=on_worker_executing,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )

            # Show final result
            console.print("\n[bold green]📊 Result:[/bold green]")
            console.print(Panel(result.text, border_style="green"))

            # Show stats
            console.print(
                f"[dim]Steps: {len(result.worker_reports)} | "
                f"Tools: {len(result.tool_calls)} | "
                f"Success: {'✓' if result.success else '✗'}[/dim]"
            )

        except Exception as e:
            logger.exception("Chat error")
            console.print(f"[red]Error: {e}[/red]")

    return 0
