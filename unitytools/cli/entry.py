"""unitytools CLI entry point."""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
import urllib.request
from pathlib import Path

from rich.console import Console

from ..core.config import Config
from ..bridges import BlenderBridge, UnityBridge
from ..tools import init_tools

console = Console()


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _bootstrap() -> tuple[Config, BlenderBridge, UnityBridge]:
    """Load config, create bridges, and register tools."""
    config = Config.load()
    _setup_logging(config.log_level)
    blender = BlenderBridge(config)
    unity = UnityBridge(config)
    init_tools(blender, unity)
    return config, blender, unity


def _api_key_label(config: Config) -> str:
    if config.provider == "ollama":
        return "[dim]not needed for Ollama[/dim]"
    if not config.api_key:
        return "[red][ERR] missing[/red]"
    if not config.api_key.startswith("sk-ant-"):
        return "[yellow][WARN] present, but invalid-looking[/yellow]"
    return "[green][OK] present[/green]"


def cmd_status(args: argparse.Namespace) -> int:
    config, blender, unity = _bootstrap()
    console.print("[bold cyan]UnityTools Status[/bold cyan]")
    console.print(f"  Project root: {config.project_root}")
    console.print(f"  Provider:     {config.provider}")
    model_label = config.ollama_model if config.provider == "ollama" else config.model
    console.print(f"  Model:        {model_label}")
    if config.provider == "ollama":
        console.print(f"  Ollama host:  {config.ollama_host}")
    console.print(f"  API key:      {_api_key_label(config)}")
    console.print(
        f"  Blender:      {'[green][OK] ' + (config.blender_executable or '') + '[/green]' if blender.is_available() else '[red][ERR] not found[/red]'}"
    )
    unity_ok = unity.connect(timeout=1.5)
    console.print(
        f"  Unity:        {'[green][OK] connected (port ' + str(config.unity_bridge_port) + ')[/green]' if unity_ok else '[yellow][WAIT] Editor not connected yet[/yellow]'}"
    )
    problems = config.validate()
    if problems:
        console.print("\n[yellow]Warnings:[/yellow]")
        for p in problems:
            console.print(f"  - {p}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    config, blender, unity = _bootstrap()
    cmd_status(args)
    console.print("\n[bold cyan]Doctor checks[/bold cyan]")
    if config.provider == "ollama":
        try:
            with urllib.request.urlopen(config.ollama_host.rstrip("/") + "/api/tags", timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            has_model = any(m == config.ollama_model for m in models)
            console.print(f"  Ollama API:   [green][OK] reachable[/green]")
            console.print(
                f"  Ollama model: {'[green][OK] installed[/green]' if has_model else '[yellow][WAIT] not installed[/yellow]'} {config.ollama_model}"
            )
            if not has_model:
                console.print(f"  Hint:         ollama pull {config.ollama_model}")
        except Exception as exc:
            console.print(f"  Ollama API:   [red][ERR] {exc}[/red]")
    console.print(
        f"  Unity ping:   {'[green][OK] responded[/green]' if unity.ping() else '[yellow][WAIT] not responding[/yellow]'}"
    )
    console.print(
        f"  Blender run:  {'[green][OK] available[/green]' if blender.is_available() else '[red][ERR] unavailable[/red]'}"
    )
    return 0


def cmd_install_unity_plugin(args: argparse.Namespace) -> int:
    project = Path(args.project).expanduser().resolve()
    assets = project / "Assets"
    packages = project / "Packages"
    manifest = packages / "manifest.json"
    if not assets.exists() or not packages.exists():
        console.print(f"[red][ERR] Not a Unity project: {project}[/red]")
        return 1
    repo_root = Path(__file__).resolve().parents[2]
    plugin_root = repo_root / "unity_plugin"
    if not plugin_root.exists():
        plugin_root = Path.cwd() / "unity_plugin"
    source = plugin_root / "Editor" / "Bridge"
    if not source.exists():
        console.print("[red][ERR] Could not find unity_plugin/Editor/Bridge in this checkout.[/red]")
        return 1
    target = assets / "Editor" / "UnityToolsBridge"
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, target / item.name)
    installed_targets = [target]

    autopilot_source = plugin_root / "Scripts" / "Autopilot"
    if autopilot_source.exists():
        autopilot_target = assets / "Scripts" / "Autopilot"
        _copy_tree_files(autopilot_source, autopilot_target, suffixes={".cs"})
        installed_targets.append(autopilot_target)

    autopilot_editor_source = plugin_root / "Editor" / "Autopilot"
    if autopilot_editor_source.exists():
        autopilot_editor_target = assets / "Editor" / "UnityToolsAutopilot"
        duplicate_names = _existing_editor_script_names(
            assets / "Editor",
            autopilot_editor_target,
            {p.name for p in autopilot_editor_source.rglob("*.cs")},
        )
        if duplicate_names:
            _remove_duplicate_editor_targets(autopilot_editor_target, duplicate_names)
            console.print(
                "[yellow][WAIT] Skipped Autopilot editor helpers because matching scripts already exist under Assets/Editor:[/yellow] "
                + ", ".join(sorted(duplicate_names))
            )
        else:
            _copy_tree_files(autopilot_editor_source, autopilot_editor_target, suffixes={".cs"})
            installed_targets.append(autopilot_editor_target)

    if manifest.exists():
        data = json.loads(manifest.read_text(encoding="utf-8-sig"))
        deps = data.setdefault("dependencies", {})
        deps.setdefault("com.unity.nuget.newtonsoft-json", "3.2.1")
        manifest.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    env_example = repo_root / ".env.example"
    env_target = project / ".env"
    if env_example.exists() and not env_target.exists():
        shutil.copy2(env_example, env_target)
    console.print("[green][OK] Installed UnityTools Unity package files:[/green]")
    for installed in installed_targets:
        console.print(f"  - {installed}")
    console.print("[dim]Open Unity, then Window > UnityTools AI > Autopilot Chat.[/dim]")
    return 0


def _copy_tree_files(source: Path, target: Path, suffixes: set[str] | None = None) -> None:
    """Copy a Unity plugin subtree without .meta files from another project."""
    target.mkdir(parents=True, exist_ok=True)
    for item in source.rglob("*"):
        if not item.is_file():
            continue
        if item.name.endswith(".meta"):
            continue
        if suffixes and item.suffix.lower() not in suffixes:
            continue
        relative = item.relative_to(source)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item, destination)


def _existing_editor_script_names(editor_root: Path, intended_target: Path, names: set[str]) -> set[str]:
    """Find same-named editor scripts outside our intended target to avoid CS0101 duplicates."""
    if not editor_root.exists():
        return set()
    intended = intended_target.resolve()
    found: set[str] = set()
    for item in editor_root.rglob("*.cs"):
        if item.name not in names:
            continue
        try:
            item.resolve().relative_to(intended)
            continue
        except ValueError:
            found.add(item.name)
    return found


def _remove_duplicate_editor_targets(target: Path, names: set[str]) -> None:
    """Clean stale copies from previous installs when root-level scripts already exist."""
    if not target.exists():
        return
    for item in target.rglob("*.cs"):
        if item.name in names:
            item.unlink(missing_ok=True)
            meta = item.with_suffix(item.suffix + ".meta")
            if meta.exists():
                meta.unlink(missing_ok=True)
    try:
        if not any(target.rglob("*")):
            target.rmdir()
    except OSError:
        pass


def cmd_chat(args: argparse.Namespace) -> int:
    config, blender, unity = _bootstrap()
    problems = config.validate()
    api_problems = [p for p in problems if "ANTHROPIC_API_KEY" in p]
    if api_problems:
        console.print(f"[red]{api_problems[0]}[/red]")
        return 1
    from .chat import run_chat
    return run_chat(config, blender, unity)


def cmd_blender_export(args: argparse.Namespace) -> int:
    from pathlib import Path as _Path
    config, blender, unity = _bootstrap()
    if not blender.is_available():
        console.print(f"[red]Blender not found: {config.blender_executable}[/red]")
        return 1
    _Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    result = blender.export_fbx(
        blend_file=args.blend,
        output_path=args.output,
        slot=args.slot,
        scale=args.scale,
    )
    if result.success:
        console.print(f"[green][OK] Export complete:[/green] {args.output}")
        return 0
    console.print(f"[red][ERR] Export failed:[/red]\n{result.stderr}")
    return 1


def cmd_unity_ping(args: argparse.Namespace) -> int:
    config, blender, unity = _bootstrap()
    if not unity.connect(timeout=2.0):
        console.print("[red]Could not connect to Unity Editor. Is the Editor open and BridgeServer running?[/red]")
        return 1
    if unity.ping():
        console.print("[green][OK] Unity Editor responded.[/green]")
        return 0
    console.print("[red][ERR] Connected, but ping failed.[/red]")
    return 1


def cmd_chat_server(args: argparse.Namespace) -> int:
    """Start the TCP chat server used by the Unity Editor window."""
    config, blender, unity = _bootstrap()
    problems = config.validate()
    api_problems = [p for p in problems if "ANTHROPIC_API_KEY" in p]
    if api_problems:
        console.print(f"[red]{api_problems[0]}[/red]")
        return 1
    from ..core.chat_server import ChatServer
    server = ChatServer(config, host=args.host, port=args.port)
    console.print(f"[cyan]Starting chat server: {args.host}:{args.port}[/cyan]")
    console.print("[dim]In Unity: Tools > UnityTools > Open Chat, then Connect.[/dim]")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")
    try:
        server.start_blocking()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping server...[/yellow]")
        server.stop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="unitytools", description="Unity + Blender Autopilot")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("status", help="Show bridge and config status")
    sub.add_parser("doctor", help="Run local provider, Unity, and Blender diagnostics")
    sub.add_parser("chat", help="Start the terminal chat REPL")
    sub.add_parser("unity-ping", help="Test the Unity Editor bridge")
    p_install = sub.add_parser("install-unity-plugin", help="Copy the Unity Editor panel, bridge, and Autopilot scripts into a Unity project")
    p_install.add_argument("--project", required=True, help="Path to the Unity project root")
    p_export = sub.add_parser("blender-export", help="Export FBX from Blender")
    p_export.add_argument("--blend", required=True, help="Path to .blend file")
    p_export.add_argument("--output", required=True, help="Output .fbx file")
    p_export.add_argument("--slot", default=None, help="Only export objects whose name contains this slot")
    p_export.add_argument("--scale", type=float, default=1.0, help="Export scale factor")
    p_chat_srv = sub.add_parser("chat-server", help="Start the TCP chat server for the Editor window")
    p_chat_srv.add_argument("--host", default="127.0.0.1")
    p_chat_srv.add_argument("--port", type=int, default=7778)
    args = parser.parse_args()
    handlers = {
        "status": cmd_status,
        "doctor": cmd_doctor,
        "chat": cmd_chat,
        "unity-ping": cmd_unity_ping,
        "install-unity-plugin": cmd_install_unity_plugin,
        "blender-export": cmd_blender_export,
        "chat-server": cmd_chat_server,
    }
    if args.cmd is None:
        parser.print_help()
        return 0
    handler = handlers.get(args.cmd)
    if handler is None:
        parser.print_help()
        return 1
    try:
        return handler(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        return 130

if __name__ == "__main__":
    sys.exit(main())
