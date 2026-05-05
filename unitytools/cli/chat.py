"""İnteraktif chat REPL'i. prompt_toolkit + rich kullanır.

Slash komutlar:
    /help        komutları göster
    /clear       konuşma geçmişini sıfırla
    /tools       mevcut tool'ları listele
    /status      bridge durumunu göster
    /quit        çık

Slash olmayan her şey LLM'e gider.
"""
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
                [("class:prompt", "❯ ")],
                style=PROMPT_STYLE,
                multiline=False,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Çıkılıyor...[/dim]")
            return 0

        if not user_in:
            continue

        # Slash komutları
        if user_in.startswith("/"):
            cmd_result = _handle_slash(user_in, orch, blender, unity)
            if cmd_result == "quit":
                return 0
            continue

        # LLM'e gönder
        _send_to_llm(orch, user_in)


def _handle_slash(line: str, orch: Orchestrator, blender: BlenderBridge, unity: UnityBridge) -> str | None:
    parts = line[1:].split()
    if not parts:
        return None
    cmd = parts[0].lower()

    if cmd in ("quit", "exit", "q"):
        console.print("[dim]Görüşürüz.[/dim]")
        return "quit"

    if cmd == "help":
        console.print(
            Panel(
                "[cyan]/help[/cyan]    bu yardımı göster\n"
                "[cyan]/clear[/cyan]   konuşma geçmişini temizle\n"
                "[cyan]/tools[/cyan]   tüm tool'ları listele\n"
                "[cyan]/status[/cyan]  bridge durumunu göster\n"
                "[cyan]/quit[/cyan]    çık\n\n"
                "[dim]Slash olmayan her mesaj Claude'a gider, gerekirse tool çağırır.[/dim]",
                title="Komutlar",
                border_style="cyan",
            )
        )
        return None

    if cmd == "clear":
        orch.reset()
        console.print("[green]✓ Geçmiş temizlendi.[/green]")
        return None

    if cmd == "tools":
        table = Table(title="Kayıtlı Tool'lar", show_lines=False)
        table.add_column("İsim", style="cyan")
        table.add_column("Açıklama")
        for spec in get_all_tools():
            table.add_row(spec.name, spec.description)
        console.print(table)
        return None

    if cmd == "status":
        console.print(f"  Blender: {'✓' if blender.is_available() else '✗'}")
        console.print(f"  Unity:   {'✓ bağlı' if unity.connect(timeout=1.0) else '✗ Editor kapalı'}")
        return None

    console.print(f"[red]Bilinmeyen komut: /{cmd}[/red]")
    return None


def _send_to_llm(orch: Orchestrator, message: str) -> None:
    def on_tool_call(name: str, params: dict) -> None:
        # Compact gösterim
        params_short = ", ".join(f"{k}={v!r}" for k, v in list(params.items())[:3])
        if len(params) > 3:
            params_short += ", ..."
        console.print(f"  [dim]→ tool:[/dim] [yellow]{name}[/yellow]({params_short})")

    def on_tool_result(name: str, result) -> None:
        ok = isinstance(result, dict) and result.get("ok", True)
        marker = "[green]✓[/green]" if ok else "[red]✗[/red]"
        console.print(f"  [dim]← {marker} {name}[/dim]")

    with console.status("[cyan]düşünüyor...[/cyan]", spinner="dots"):
        try:
            result = orch.chat(message, on_tool_call=on_tool_call, on_tool_result=on_tool_result)
        except Exception as e:
            console.print(f"[red]Hata:[/red] {e}")
            return

    if result.text:
        console.print(Panel(Markdown(result.text), border_style="green", title="Claude"))
    if result.stop_reason == "max_iterations":
        console.print("[yellow]⚠ Max iterasyon limitine ulaşıldı.[/yellow]")


def _print_welcome(config: Config, blender: BlenderBridge, unity: UnityBridge) -> None:
    blender_ok = "✓" if blender.is_available() else "✗"
    unity_ok = "✓ bağlı" if unity.connect(timeout=1.0) else "○ kapalı (sonra bağlanırız)"
    console.print(
        Panel(
            f"[bold]UnityTools Chat[/bold]\n"
            f"Provider: [cyan]{config.provider}[/cyan]   "
            f"Model: [cyan]{model_label}[/cyan]   "
            f"Blender: [cyan]{blender_ok}[/cyan]   "
            f"Unity: [cyan]{unity_ok}[/cyan]\n\n"
            f"[dim]/help yazarak komutları gör, /quit ile çık.[/dim]",
            border_style="cyan",
        )
    )
