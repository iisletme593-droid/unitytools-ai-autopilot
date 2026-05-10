"""unitytools CLI entry point."""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

from rich.console import Console

from ..core.config import Config
from ..bridges import BlenderBridge, UnityBridge, UnrealBridge
from ..tools import init_tools

console = Console()


def _ollama_installed_models(config: Config) -> set[str]:
    try:
        with urllib.request.urlopen(f"{config.ollama_host.rstrip('/')}/api/tags", timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {m.get("name", "") for m in data.get("models", []) if isinstance(m, dict)}
    except Exception:
        return set()


def _resolve_ollama_model(config: Config, requested: str, fallback: str) -> str:
    requested = requested or fallback
    fallback = fallback or config.ollama_model
    installed = _ollama_installed_models(config)
    if not installed:
        return requested
    if requested in installed:
        return requested
    if fallback in installed:
        console.print(f"[yellow]Model {requested!r} not installed; falling back to {fallback!r}.[/yellow]")
        return fallback
    if config.ollama_model in installed:
        console.print(f"[yellow]Model {requested!r} not installed; falling back to {config.ollama_model!r}.[/yellow]")
        return config.ollama_model
    return requested


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
    unreal = UnrealBridge(config)
    init_tools(blender, unity, unreal)
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
    unreal = UnrealBridge(config)
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
    unreal_ok = unreal.connect(timeout=1.0)
    console.print(
        f"  Unreal:       {'[green][OK] connected (port ' + str(config.unreal_bridge_port) + ')[/green]' if unreal_ok else '[yellow][WAIT] Editor not connected yet[/yellow]'}"
    )
    problems = config.validate()
    if problems:
        console.print("\n[yellow]Warnings:[/yellow]")
        for p in problems:
            console.print(f"  - {p}")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    config, blender, unity = _bootstrap()
    unreal = UnrealBridge(config)
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
        f"  Unreal ping:  {'[green][OK] responded[/green]' if unreal.ping() else '[yellow][WAIT] not responding[/yellow]'}"
    )
    console.print(
        f"  Blender run:  {'[green][OK] available[/green]' if blender.is_available() else '[red][ERR] unavailable[/red]'}"
    )
    return 0


def cmd_cleanup_processes(args: argparse.Namespace) -> int:
    """Stop stale embedded chat-server processes left after Unity quits."""
    if os.name != "nt":
        console.print("[yellow]cleanup-processes is currently Windows-only.[/yellow]")
        return 0
    ps = r"""
$items = Get-CimInstance Win32_Process |
  Where-Object { ($_.Name -in @('unitytools.exe','python.exe')) -and ($_.CommandLine -match 'unitytools(\.exe)?"? chat-server|-m unitytools\.cli\.entry chat-server') }
foreach ($item in $items) {
  try {
    Stop-Process -Id $item.ProcessId -Force -ErrorAction Stop
    Write-Output "stopped $($item.ProcessId) $($item.Name)"
  } catch {
    Write-Output "already stopped $($item.ProcessId) $($item.Name)"
  }
}
"""
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "").strip()
    if output:
        console.print(output)
    else:
        console.print("[green][OK] No stale UnityTools chat-server processes found.[/green]")
    return 0 if proc.returncode == 0 else proc.returncode


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


def cmd_install_unreal_plugin(args: argparse.Namespace) -> int:
    project = Path(args.project).expanduser().resolve()
    if project.suffix.lower() == ".uproject":
        uproject = project
        project_root = project.parent
    else:
        project_root = project
        candidates = list(project_root.glob("*.uproject"))
        if not candidates:
            console.print(f"[red][ERR] Not an Unreal project: {project}[/red]")
            return 1
        uproject = candidates[0]

    repo_root = Path(__file__).resolve().parents[2]
    source = repo_root / "unreal_plugin"
    if not source.exists():
        source = Path.cwd() / "unreal_plugin"
    if not (source / "UnrealToolsBridge.uplugin").exists():
        console.print("[red][ERR] Could not find unreal_plugin/UnrealToolsBridge.uplugin in this checkout.[/red]")
        return 1

    target = project_root / "Plugins" / "UnrealToolsBridge"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    _enable_unreal_plugin(uproject, "UnrealToolsBridge")
    console.print("[green][OK] Installed UnrealToolsBridge:[/green]")
    console.print(f"  - {target}")
    console.print(f"  - Enabled in {uproject.name}")
    console.print("[dim]Open/restart Unreal Editor, enable PythonScriptPlugin if prompted, then run: unitytools unreal-ping[/dim]")
    return 0


def _enable_unreal_plugin(uproject: Path, plugin_name: str) -> None:
    data = json.loads(uproject.read_text(encoding="utf-8-sig"))
    plugins = data.setdefault("Plugins", [])
    for item in plugins:
        if item.get("Name") == plugin_name:
            item["Enabled"] = True
            break
    else:
        plugins.append({"Name": plugin_name, "Enabled": True})
    for required in ("PythonScriptPlugin", "EditorScriptingUtilities"):
        for item in plugins:
            if item.get("Name") == required:
                item["Enabled"] = True
                break
        else:
            plugins.append({"Name": required, "Enabled": True})
    uproject.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cmd_unreal_ping(args: argparse.Namespace) -> int:
    config, blender, unity = _bootstrap()
    unreal = UnrealBridge(config)
    if not unreal.connect(timeout=2.0):
        console.print("[red]Could not connect to Unreal Editor. Is the Editor open and UnrealToolsBridge running?[/red]")
        return 1
    if unreal.ping():
        console.print("[green][OK] Unreal Editor responded.[/green]")
        return 0
    console.print("[red][ERR] Connected, but ping failed.[/red]")
    return 1


def cmd_migrate_unity_assets_to_unreal(args: argparse.Namespace) -> int:
    from ..tools.unreal_tools import unreal_stage_unity_assets_for_migration, unreal_import_asset, unreal_save_dirty_packages

    config, blender, unity = _bootstrap()
    UnrealBridge(config).connect(timeout=1.0)
    staged = unreal_stage_unity_assets_for_migration(
        unity_project=args.unity_project,
        staging_dir=args.staging,
        max_files=args.max_files,
    )
    if not staged.get("ok"):
        console.print(f"[red][ERR] {staged.get('error')}[/red]")
        return 1
    console.print(f"[green][OK] Staged {staged.get('copied_count')} files[/green] -> {staged.get('staging')}")
    if not args.import_into_unreal:
        console.print("[dim]Use --import-into-unreal while Unreal Editor is open to import staged files.[/dim]")
        return 0
    staging_root = Path(staged.get("staging", args.staging))
    import_exts = {".fbx", ".obj", ".glb", ".gltf", ".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".exr", ".wav", ".mp3"}
    files = [p for p in staging_root.rglob("*") if p.is_file() and p.suffix.lower() in import_exts]
    files.sort(key=lambda p: (_unreal_import_priority(p), str(p).lower()))
    manifest_path = staging_root / "unreal_import_manifest.json"
    manifest = _load_unreal_import_manifest(manifest_path) if args.resume else {"imported": {}, "failed": {}}
    imported_map = manifest.setdefault("imported", {})
    failed_map = manifest.setdefault("failed", {})
    selected_files: list[Path] = []
    pre_skipped = 0
    for path in files:
        key = str(path)
        if args.resume and key in imported_map:
            pre_skipped += 1
            continue
        if args.resume and not args.retry_failed and key in failed_map:
            pre_skipped += 1
            continue
        selected_files.append(path)
        if args.import_limit and args.import_limit > 0 and len(selected_files) >= args.import_limit:
            break
    files = selected_files
    imported = 0
    failed = 0
    skipped = pre_skipped
    for index, path in enumerate(files, start=1):
        key = str(path)
        destination = args.destination.rstrip("/")
        if args.category_folders:
            rel = path.relative_to(staging_root)
            parent_parts = rel.parts[:-1] or ("Root",)
            destination = "/".join([destination] + [_unreal_safe_path_segment(part) for part in parent_parts])
        result = unreal_import_asset(
            str(path),
            destination=destination,
            replace_existing=args.replace_existing,
            save=False,
            import_mode=args.import_mode,
        )
        if result.get("ok"):
            imported += 1
            imported_map[key] = {"destination": destination, "objects": result.get("imported_object_paths", [])}
            failed_map.pop(key, None)
        else:
            if "not connected" in str(result.get("error", "")).lower() or "connection lost" in str(result.get("error", "")).lower():
                import time
                time.sleep(3)
                result = unreal_import_asset(
                    str(path),
                    destination=destination,
                    replace_existing=args.replace_existing,
                    save=False,
                    import_mode=args.import_mode,
                )
                if result.get("ok"):
                    imported += 1
                    imported_map[key] = {"destination": destination, "objects": result.get("imported_object_paths", [])}
                    failed_map.pop(key, None)
                    continue
            failed += 1
            failed_map[key] = {"destination": destination, "error": result.get("error", "unknown error")}
            console.print(f"[yellow][WAIT] Import failed {path}: {result.get('error')}[/yellow]")
        if index % max(1, args.batch_size) == 0:
            _save_unreal_import_manifest(manifest_path, manifest)
            unreal_save_dirty_packages()
            console.print(f"[dim]Progress: {index}/{len(files)} scanned, imported {imported}, skipped {skipped}, failed {failed}[/dim]")
    _save_unreal_import_manifest(manifest_path, manifest)
    unreal_save_dirty_packages()
    console.print(f"[green][OK] Imported {imported}/{len(files)} files into Unreal[/green]")
    if skipped:
        console.print(f"[dim]Skipped {skipped} already imported files via resume manifest.[/dim]")
    console.print(f"[dim]Manifest: {manifest_path}[/dim]")
    if failed:
        console.print(f"[yellow][WAIT] {failed} files failed. Some Unity-specific files or unsupported GLB variants may need conversion.[/yellow]")
    return 0


def _load_unreal_import_manifest(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"imported": {}, "failed": {}}


def _save_unreal_import_manifest(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _unreal_safe_path_segment(value: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
    cleaned = "".join(ch if ch in allowed else "_" for ch in value.strip())
    return cleaned.strip("_") or "Imported"


def _unreal_import_priority(path: Path) -> tuple[int, str]:
    ext = path.suffix.lower()
    if ext in {".png", ".jpg", ".jpeg", ".tga", ".tif", ".tiff", ".exr"}:
        return (0, ext)
    if ext in {".wav", ".mp3"}:
        return (1, ext)
    if ext in {".obj"}:
        return (2, ext)
    if ext in {".glb", ".gltf"}:
        return (3, ext)
    if ext == ".fbx":
        return (4, ext)
    return (9, ext)


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


def cmd_dual_chat(args: argparse.Namespace) -> int:
    config, blender, unity = _bootstrap()
    # Dual-agent only works with Ollama
    if config.provider != "ollama":
        console.print("[red]Dual-agent mode requires UNITYTOOLS_PROVIDER=ollama[/red]")
        return 1
    from .dual_chat import run_dual_chat
    master = args.master or "qwen3.6:latest"
    worker = args.worker or "qwen2.5:14b-instruct"
    reader = getattr(args, "reader", None) or "qwen2.5:14b-instruct"
    master = _resolve_ollama_model(config, master, config.ollama_model)
    worker = _resolve_ollama_model(config, worker, config.ollama_model)
    reader = _resolve_ollama_model(config, reader, config.ollama_model)
    return run_dual_chat(config, master, worker, reader)


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


def cmd_studio_init(args: argparse.Namespace) -> int:
    from ..studio.paths import StudioPaths
    from ..studio.templates import starter_files

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        console.print(f"[red][ERR] Project root does not exist: {project}[/red]")
        return 1
    paths = StudioPaths(project_root=project)
    if paths.exists() and not args.force:
        console.print(
            f"[yellow]studio/ already exists at {paths.root}.[/yellow] "
            "Use --force to overwrite starter docs (existing JSON/JSONL is preserved either way)."
        )
        return 1

    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    skipped: list[Path] = []
    for rel, content in starter_files().items():
        target = paths.root / rel
        if target.exists() and not args.force:
            skipped.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")
        written.append(target)

    if not paths.backlog.exists():
        paths.backlog.write_text(
            json.dumps({"tasks": []}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(paths.backlog)
    if not paths.milestones.exists():
        paths.milestones.write_text(
            json.dumps({"milestones": []}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(paths.milestones)
    if not paths.decisions.exists():
        paths.decisions.write_text("", encoding="utf-8")
        written.append(paths.decisions)

    console.print(f"[green][OK] Studio initialized at[/green] {paths.root}")
    for p in written:
        console.print(f"  + {p.relative_to(project)}")
    for p in skipped:
        console.print(f"  [dim]= {p.relative_to(project)} (kept existing)[/dim]")
    console.print(
        "[dim]Next: open studio/gdd.md and write your one-page pitch, then `unitytools studio status`.[/dim]"
    )
    return 0


def cmd_studio_status(args: argparse.Namespace) -> int:
    from ..studio.paths import StudioPaths
    from ..studio.state import StudioState

    project = Path(args.project).expanduser().resolve()
    paths = StudioPaths(project_root=project)
    if not paths.exists():
        console.print(
            f"[yellow]No studio at {paths.root}.[/yellow] Run `unitytools studio init --project {project}` first."
        )
        return 1
    state = StudioState(paths)
    summary = state.summary()
    console.print(f"[bold cyan]Studio[/bold cyan] {summary['studio_root']}")
    console.print(
        f"  Docs: GDD {'[green][OK][/green]' if summary['has_gdd'] else '[red]missing[/red]'}, "
        f"Art Bible {'[green][OK][/green]' if summary['has_art_bible'] else '[red]missing[/red]'}, "
        f"Sprint {'[green][OK][/green]' if summary['has_sprint'] else '[red]missing[/red]'}"
    )
    console.print(f"  Tasks:      {summary['task_count']}")
    if summary["tasks_by_status"]:
        for status, count in sorted(summary["tasks_by_status"].items()):
            console.print(f"    - {status:<12} {count}")
    if summary["tasks_by_role"]:
        console.print("  By role:")
        for role, count in sorted(summary["tasks_by_role"].items()):
            console.print(f"    - {role:<14} {count}")
    console.print(f"  Milestones: {summary['milestone_count']}")
    console.print(f"  Decisions:  {summary['decision_count']}")
    return 0


def cmd_studio_run(args: argparse.Namespace) -> int:
    """Run a single studio role against the project state with a brief."""
    from ..studio import (
        StudioPaths,
        StudioState,
        get_role,
        has_rehearsal_for,
        init_studio_tools,
        init_studio_unity,
        init_studio_vision,
        make_default_client,
        make_default_vision_client,
        RehearsalLLM,
        RoleRunner,
        all_roles,
    )

    project = Path(args.project).expanduser().resolve()
    paths = StudioPaths(project_root=project)
    if not paths.exists():
        console.print(
            f"[yellow]No studio at {paths.root}.[/yellow] Run `unitytools studio-init --project {project}` first."
        )
        return 1
    try:
        role = get_role(args.role)
    except KeyError:
        names = ", ".join(r.id for r in all_roles())
        console.print(f"[red]Unknown role {args.role!r}. Choose one of: {names}[/red]")
        return 1

    state = StudioState(paths)
    init_studio_tools(state)

    config, _, unity = _bootstrap()
    if args.dry_run:
        if not has_rehearsal_for(role.id):
            console.print(
                f"[yellow]No rehearsal script for role {role.id!r}. Available: producer, designer, critic.[/yellow]"
            )
            return 1
        console.print("[dim]Dry-run: using RehearsalLLM (no API calls).[/dim]")
        client = RehearsalLLM(role.id)
    else:
        try:
            client = make_default_client(config, model_override=args.model or None)
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
        if config.provider == "ollama":
            console.print(f"[dim]Provider: ollama, model: {getattr(client, 'model', config.ollama_model)}.[/dim]")

    # Engine + vision bridges are only wired up when the role needs them. That
    # way `studio-run --role designer` still works without Unity / vision API.
    needs_engine = "studio_capture_screenshot" in role.tool_set
    needs_vision = "studio_compare_to_reference" in role.tool_set
    if needs_engine:
        if unity.connect(timeout=2.0):
            init_studio_unity(unity)
            console.print("[dim]Unity bridge connected for screenshot capture.[/dim]")
        else:
            console.print(
                "[yellow]Unity Editor not connected -- studio_capture_screenshot will report not-connected. "
                "Open Unity and try again, or run a non-engine role.[/yellow]"
            )
            init_studio_unity(unity)  # tool itself returns the error nicely
    if needs_vision:
        try:
            init_studio_vision(make_default_vision_client(config))
            console.print("[dim]Vision client ready (Anthropic Claude).[/dim]")
        except RuntimeError as exc:
            console.print(
                f"[yellow]Vision client unavailable: {exc}[/yellow] "
                "[dim](studio_compare_to_reference will return an error.)[/dim]"
            )

    runner = RoleRunner(client, max_iterations=args.max_iterations)
    brief = args.brief or _default_brief_for(role.id)
    console.print(f"[cyan]Running role[/cyan] [bold]{role.name}[/bold] ({role.id})")
    console.print(f"[dim]Brief:[/dim] {brief}")

    def _on_tool_call(name: str, params: dict) -> None:
        console.print(f"  [dim]-> {name}({_short_kwargs(params)})[/dim]")

    def _on_tool_result(name: str, result: Any) -> None:
        ok = isinstance(result, dict) and result.get("ok", True)
        marker = "[green][OK][/green]" if ok else "[red][ERR][/red]"
        console.print(f"  [dim]<- {name}[/dim] {marker}")

    result = runner.run(role, brief, on_tool_call=_on_tool_call, on_tool_result=_on_tool_result)
    console.print(
        f"\n[bold]Done[/bold] -- iterations={result.iterations}, "
        f"tool_calls={len(result.tool_calls)}, stop={result.stop_reason}"
    )
    if result.text:
        console.print("\n[bold cyan]Role output[/bold cyan]")
        console.print(result.text)
    return 0


def cmd_studio_autopilot(args: argparse.Namespace) -> int:
    """Walk the backlog and run the right role for each pending task.

    With --dry-run, every dispatched role uses a RehearsalLLM and tasks
    that target the Worker (engine work) are skipped — there's nothing
    productive a no-network rehearsal can do in Unity.
    """
    from ..studio import (
        Dispatcher,
        StudioPaths,
        StudioState,
        RehearsalLLM,
        has_rehearsal_for,
        init_studio_tools,
        make_default_client,
        make_default_vision_client,
    )

    project = Path(args.project).expanduser().resolve()
    paths = StudioPaths(project_root=project)
    if not paths.exists():
        console.print(
            f"[yellow]No studio at {paths.root}.[/yellow] Run `unitytools studio-init --project {project}` first."
        )
        return 1
    state = StudioState(paths)
    init_studio_tools(state)

    config, _, unity = _bootstrap()

    # Build the per-role client factory: one constant client in production,
    # one fresh RehearsalLLM per role in dry-run.
    if args.dry_run:
        def client_factory(role_id: str):
            if not has_rehearsal_for(role_id):
                # Caller checks needs_engine first, but be defensive: fall back
                # to an "out of script" rehearsal that prints a message and stops.
                return RehearsalLLM(role_id)
            return RehearsalLLM(role_id)
        console.print("[dim]Dry-run: RehearsalLLM per role, no API calls.[/dim]")
    else:
        try:
            shared_client = make_default_client(config, model_override=args.model or None)
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
        if config.provider == "ollama":
            console.print(
                f"[dim]Provider: ollama, model: {getattr(shared_client, 'model', config.ollama_model)}.[/dim]"
            )

        def client_factory(role_id: str):
            return shared_client

    # Engine + vision wiring — only attempted when dispatch has tasks
    # that need it. Dispatcher's _can_run() consults these.
    bridge_for_dispatcher: object | None = None
    vision_for_dispatcher = None
    if not args.dry_run:
        if unity.connect(timeout=2.0):
            bridge_for_dispatcher = unity
            console.print("[dim]Unity bridge connected.[/dim]")
        else:
            console.print("[yellow]Unity not connected; engine-bound tasks will be skipped.[/yellow]")
        try:
            vision_for_dispatcher = make_default_vision_client(config)
            console.print("[dim]Vision client ready.[/dim]")
        except RuntimeError:
            console.print("[yellow]Vision client unavailable; compare-tool calls will return errors.[/yellow]")

    only_roles = tuple(args.only_role) if args.only_role else None
    dispatcher = Dispatcher(
        state,
        client_factory,
        unity_bridge=bridge_for_dispatcher,
        vision_client=vision_for_dispatcher,
        max_iterations=args.max_iterations,
    )

    console.print(f"[cyan]Autopilot[/cyan] -- max-tasks={args.max_tasks}")
    summary = dispatcher.dispatch_pending(limit=args.max_tasks, only_roles=only_roles)

    if not summary.results:
        console.print("[dim]No pending tasks matched. Backlog is clean (or filtered out).[/dim]")
        return 0

    for r in summary.results:
        marker = {
            "completed": "[green][OK][/green]",
            "blocked": "[yellow][BLOCK][/yellow]",
            "review": "[cyan][REVIEW][/cyan]",
            "skipped": "[dim][SKIP][/dim]",
            "error": "[red][ERR][/red]",
        }.get(r.action, r.action.upper())
        suffix = f" -- {r.reason}" if r.reason else ""
        console.print(f"  {marker} {r.task_id} ({r.target_role or '?'}): {r.task_title}{suffix}")

    counts = summary.by_action()
    parts = [f"{action}={n}" for action, n in sorted(counts.items())]
    console.print(f"\n[bold]Done[/bold] -- {summary.total} task(s): {', '.join(parts)}")
    return 0


def cmd_studio_execute(args: argparse.Namespace) -> int:
    """Pick a backlog task and run the Worker against it.

    Lifecycle:
      pending|review -> in_progress  (we set this before the Worker starts)
      Worker is told to flip to "done" or "blocked" via studio_update_task_status.
      If the Worker forgets, we leave the status as in_progress and warn.
    """
    from ..studio import (
        StudioPaths,
        StudioState,
        TaskStatus,
        WORKER,
        RoleRunner,
        init_studio_tools,
        init_studio_unity,
        init_studio_vision,
        make_default_client,
        make_default_vision_client,
    )

    project = Path(args.project).expanduser().resolve()
    paths = StudioPaths(project_root=project)
    if not paths.exists():
        console.print(
            f"[yellow]No studio at {paths.root}.[/yellow] Run `unitytools studio-init --project {project}` first."
        )
        return 1
    state = StudioState(paths)
    init_studio_tools(state)

    # Find the task
    tasks = state.load_tasks()
    target = next((t for t in tasks if t.id == args.task_id), None)
    if target is None:
        console.print(f"[red]Task {args.task_id!r} not found in backlog.[/red]")
        return 1

    if target.status in (TaskStatus.DONE, TaskStatus.REJECTED) and not args.force:
        console.print(
            f"[yellow]Task is already {target.status.value}.[/yellow] Use --force to re-run."
        )
        return 1

    config, _, unity = _bootstrap()
    try:
        client = make_default_client(config, model_override=args.model or None)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    if not unity.connect(timeout=2.0):
        console.print(
            "[red]Unity Editor is not connected. Open Unity and start the BridgeServer before executing tasks.[/red]"
        )
        return 1
    init_studio_unity(unity)

    # Vision is optional but strongly recommended for the Worker's verify step.
    try:
        init_studio_vision(make_default_vision_client(config))
    except RuntimeError as exc:
        console.print(f"[yellow]Vision unavailable: {exc} -- verify step will skip the compare.[/yellow]")

    # Mark in-progress before the Worker runs so concurrent dashboards see it.
    target.status = TaskStatus.IN_PROGRESS
    state.update_task(target)

    brief = (
        f"Pick up backlog task and execute it now.\n\n"
        f"Task id: {target.id}\n"
        f"Title: {target.title}\n"
        f"Description: {target.description or '(none)'}\n"
        f"Owning role: {target.role}\n"
        f"Milestone: {target.milestone or '(none)'}\n"
    )
    if args.extra:
        brief += "\nExtra context: " + args.extra.strip() + "\n"

    runner = RoleRunner(client, max_iterations=args.max_iterations)
    console.print(f"[cyan]Worker executing[/cyan] task {target.id}: [bold]{target.title}[/bold]")

    def _on_call(name: str, params: dict) -> None:
        console.print(f"  [dim]-> {name}({_short_kwargs(params)})[/dim]")

    def _on_result(name: str, result: Any) -> None:
        ok = isinstance(result, dict) and result.get("ok", True)
        console.print(f"  [dim]<- {name}[/dim] {'[green][OK][/green]' if ok else '[red][ERR][/red]'}")

    result = runner.run(WORKER, brief, on_tool_call=_on_call, on_tool_result=_on_result)

    # Did the Worker actually flip the status? Reload from disk.
    final_task = next((t for t in state.load_tasks() if t.id == target.id), None)
    if final_task is None:
        console.print("[red]Task vanished from backlog while Worker was running.[/red]")
        return 1
    if final_task.status is TaskStatus.IN_PROGRESS:
        console.print(
            "[yellow]Worker did not update task status. Marking 'review' so a Critic can decide.[/yellow]"
        )
        final_task.status = TaskStatus.REVIEW
        state.update_task(final_task)

    console.print(
        f"\n[bold]Worker done[/bold] -- final status: {final_task.status.value}, "
        f"iterations={result.iterations}, tools={len(result.tool_calls)}"
    )
    if result.text:
        console.print("\n[bold cyan]Worker output[/bold cyan]")
        console.print(result.text)
    return 0


def cmd_studio_review(args: argparse.Namespace) -> int:
    """Run the Producer with a standup or retro brief and write studio/reviews/<date>.md."""
    from ..studio import (
        StudioPaths,
        StudioState,
        PRODUCER,
        RehearsalLLM,
        RoleRunner,
        init_studio_tools,
        make_default_client,
        run_review,
    )

    project = Path(args.project).expanduser().resolve()
    paths = StudioPaths(project_root=project)
    if not paths.exists():
        console.print(f"[yellow]No studio at {paths.root}.[/yellow] Run `unitytools studio-init --project {project}` first.")
        return 1
    state = StudioState(paths)
    init_studio_tools(state)

    config, _, _ = _bootstrap()
    if args.dry_run:
        console.print("[dim]Dry-run: using RehearsalLLM (no API calls).[/dim]")
        client = RehearsalLLM("producer")
    else:
        try:
            client = make_default_client(config, model_override=args.model or None)
        except RuntimeError as exc:
            console.print(f"[red]{exc}[/red]")
            return 1
    runner = RoleRunner(client, max_iterations=args.max_iterations)

    console.print(f"[cyan]Producer review -- phase={args.phase}[/cyan]")
    result, record = run_review(state, runner, phase=args.phase, extra_brief=args.extra)
    console.print(
        f"[green][OK][/green] iterations={result.iterations}, tools={len(result.tool_calls)}, "
        f"stop={result.stop_reason}"
    )
    console.print(f"[dim]Wrote {record.path}[/dim]")
    if result.text:
        console.print("\n[bold]Summary[/bold]")
        console.print(result.text)
    return 0


def cmd_studio_loop(args: argparse.Namespace) -> int:
    """Run the Producer review on a recurring cadence. --once exits after one pass."""
    from ..studio import (
        StudioPaths,
        StudioState,
        RoleRunner,
        init_studio_tools,
        make_default_client,
        LoopRunner,
    )

    project = Path(args.project).expanduser().resolve()
    paths = StudioPaths(project_root=project)
    if not paths.exists():
        console.print(f"[yellow]No studio at {paths.root}.[/yellow] Run `unitytools studio-init --project {project}` first.")
        return 1
    state = StudioState(paths)
    init_studio_tools(state)

    config, _, _ = _bootstrap()
    try:
        client = make_default_client(config, model_override=args.model or None)
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1
    runner = RoleRunner(client, max_iterations=args.max_iterations)
    loop = LoopRunner(state, runner)

    interval_hours = max(0.0, float(args.interval_hours))
    interval_seconds = interval_hours * 3600.0
    if args.once:
        console.print("[cyan]Producer loop -- single pass[/cyan]")
    else:
        console.print(f"[cyan]Producer loop -- every {interval_hours:g}h (Ctrl+C to stop)[/cyan]")
    try:
        stats = loop.run(once=args.once, interval_seconds=interval_seconds, max_iterations=args.max_passes)
    except KeyboardInterrupt:
        console.print("\n[yellow]Loop interrupted.[/yellow]")
        return 130
    console.print(f"[green][OK][/green] passes={stats.iterations}, last_phase={stats.last_phase}")
    if stats.last_record:
        console.print(f"[dim]Last review: {stats.last_record.path}[/dim]")
    return 0


def _default_brief_for(role_id: str) -> str:
    return {
        "producer": "Plan the next round of work. Read state, decide priorities, open up to 5 tasks. End with a 3-line summary.",
        "designer": "Read the current GDD and produce the smallest coherent improvement. If empty, draft a one-page initial GDD.",
        "critic": "Review the project for inconsistency between GDD, art bible, and recent decisions. Report top findings.",
        "level_designer": "Pick a reference from studio/refs/, capture the current scene, compare them, and file follow-up tasks for any missing or misplaced items.",
        "art_director": "Audit the current scene's palette against the dominant reference and the Art Bible. Update the bible only if the audit reveals a real direction shift; otherwise file tasks.",
    }.get(role_id, "Run your role on the current project state.")


def _short_kwargs(params: dict) -> str:
    if not params:
        return ""
    parts = []
    for key, value in list(params.items())[:3]:
        if isinstance(value, str) and len(value) > 40:
            value = value[:37] + "..."
        parts.append(f"{key}={value!r}")
    if len(params) > 3:
        parts.append("...")
    return ", ".join(parts)


def cmd_chat_server(args: argparse.Namespace) -> int:
    """Start the TCP chat server used by the Unity Editor window."""
    config, blender, unity = _bootstrap()
    problems = config.validate()
    api_problems = [p for p in problems if "ANTHROPIC_API_KEY" in p]
    if api_problems and config.provider == "anthropic":
        console.print(f"[red]{api_problems[0]}[/red]")
        return 1
    
    # Check if dual-agent mode is enabled
    force_single = getattr(args, 'no_dual_agent', False)
    use_dual = False if force_single else getattr(args, 'use_dual_agent', False)
    master_model = getattr(args, 'master', "qwen3.6:latest")
    worker_model = getattr(args, 'worker', "qwen2.5:14b-instruct")
    reader_model = getattr(args, 'reader', "qwen2.5:14b-instruct")
    enable_memory = getattr(args, 'enable_memory', True)
    enable_context = getattr(args, 'enable_context', True)
    
    # Auto-detect from environment
    if not use_dual and not force_single:
        import os
        use_dual_env = os.getenv("USE_DUAL_AGENT", "").lower()
        use_dual = use_dual_env in ("true", "1", "yes")
        if use_dual:
            master_model = os.getenv("DUAL_AGENT_MASTER", master_model)
            worker_model = os.getenv("DUAL_AGENT_WORKER", worker_model)
            reader_model = os.getenv("DUAL_AGENT_READER", reader_model)

    if use_dual and config.provider == "ollama":
        master_model = _resolve_ollama_model(config, master_model, config.ollama_model)
        worker_model = _resolve_ollama_model(config, worker_model, config.ollama_model)
        reader_model = _resolve_ollama_model(config, reader_model, config.ollama_model)
    
    from ..core.chat_server import ChatServer
    server = ChatServer(
        config,
        host=args.host,
        port=args.port,
        use_dual_agent=use_dual,
        master_model=master_model,
        worker_model=worker_model,
        reader_model=reader_model,
        enable_memory=enable_memory,
        enable_context=enable_context,
        engine_context=getattr(args, "engine", "auto"),
    )
    
    mode_label = f"dual-agent (Reader: {reader_model}, Master: {master_model}, Worker: {worker_model})" if use_dual else "single-agent"
    if use_dual and (enable_memory or enable_context):
        features = []
        if enable_memory:
            features.append("Memory")
        if enable_context:
            features.append("Context")
        mode_label += f" + {', '.join(features)}"
    
    console.print(f"[cyan]Starting chat server: {args.host}:{args.port} ({mode_label})[/cyan]")
    console.print("[dim]In Unity: Tools > UnityTools > Open Chat, then Connect.[/dim]")
    if use_dual:
        console.print("[yellow]Dual-agent mode: Master plans, Worker executes. Use it for complex tasks; single-agent is faster for simple edits.[/yellow]")
        if enable_memory:
            console.print("[green]Memory enabled: Learning from experiences[/green]")
        if enable_context:
            console.print("[green]Context enabled: Scene-aware planning[/green]")
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
    sub.add_parser("cleanup-processes", help="Stop stale embedded UnityTools chat-server processes")
    sub.add_parser("chat", help="Start the terminal chat REPL")
    p_dual = sub.add_parser("dual-chat", help="Start dual-agent chat (Qwen 3.6 planner + Qwen 2.5 reader/worker by default)")
    p_dual.add_argument("--master", default="qwen3.6:latest", help="Master model for planning (default: qwen3.6:latest, falls back if missing)")
    p_dual.add_argument("--worker", default="qwen2.5:14b-instruct", help="Worker model for execution (default: qwen2.5:14b-instruct)")
    p_dual.add_argument("--reader", default="qwen2.5:14b-instruct", help="Fast reader/context model (default: qwen2.5:14b-instruct)")
    sub.add_parser("unity-ping", help="Test the Unity Editor bridge")
    p_install = sub.add_parser("install-unity-plugin", help="Copy the Unity Editor panel, bridge, and Autopilot scripts into a Unity project")
    p_install.add_argument("--project", required=True, help="Path to the Unity project root")
    p_unreal_install = sub.add_parser("install-unreal-plugin", help="Copy the Unreal Editor bridge plugin into an Unreal project")
    p_unreal_install.add_argument("--project", required=True, help="Path to .uproject or Unreal project root")
    sub.add_parser("unreal-ping", help="Test the Unreal Editor bridge")
    p_migrate = sub.add_parser("migrate-unity-assets-to-unreal", help="Stage Unity source assets and optionally import them into Unreal")
    p_migrate.add_argument("--unity-project", required=True, help="Path to Unity project root")
    p_migrate.add_argument("--staging", default="UnrealMigrationStaging", help="Folder for copied source assets")
    p_migrate.add_argument("--destination", default="/Game/UnityMigrated", help="Unreal Content Browser destination")
    p_migrate.add_argument("--max-files", type=int, default=5000)
    p_migrate.add_argument("--import-into-unreal", action="store_true", help="Import staged files through the Unreal bridge")
    p_migrate.add_argument("--replace-existing", action="store_true", default=True, help="Replace assets inside the migration destination to avoid Unreal import prompts (default: true)")
    p_migrate.add_argument("--no-replace-existing", dest="replace_existing", action="store_false", help="Do not replace existing migrated assets")
    p_migrate.add_argument("--import-limit", type=int, default=0, help="Limit imported files after staging; 0 means import all staged files")
    p_migrate.add_argument("--category-folders", action="store_true", help="Preserve the first Unity Assets folder as Unreal destination subfolder")
    p_migrate.add_argument("--batch-size", type=int, default=25, help="Save packages and manifest every N imported files")
    p_migrate.add_argument("--resume", action="store_true", default=True, help="Skip files already imported in the staging manifest (default: true)")
    p_migrate.add_argument("--no-resume", dest="resume", action="store_false", help="Ignore existing migration manifest")
    p_migrate.add_argument("--retry-failed", action="store_true", help="Retry files recorded as failed in the migration manifest")
    p_migrate.add_argument("--import-mode", choices=["safe_static", "auto"], default="safe_static", help="safe_static imports FBX as static mesh to avoid broken skeleton stalls")
    p_export = sub.add_parser("blender-export", help="Export FBX from Blender")
    p_export.add_argument("--blend", required=True, help="Path to .blend file")
    p_export.add_argument("--output", required=True, help="Output .fbx file")
    p_export.add_argument("--slot", default=None, help="Only export objects whose name contains this slot")
    p_export.add_argument("--scale", type=float, default=1.0, help="Export scale factor")
    p_studio_init = sub.add_parser("studio-init", help="Scaffold studio/ project state (GDD, backlog, decisions, art bible)")
    p_studio_init.add_argument("--project", default=".", help="Project root that should contain studio/ (default: cwd)")
    p_studio_init.add_argument("--force", action="store_true", help="Overwrite starter docs if they already exist (JSON state is always preserved)")
    p_studio_status = sub.add_parser("studio-status", help="Show studio task / decision / milestone counts")
    p_studio_status.add_argument("--project", default=".", help="Project root containing studio/ (default: cwd)")
    p_studio_run = sub.add_parser("studio-run", help="Run one studio role (producer | designer | critic) against the current project state")
    p_studio_run.add_argument("--project", default=".", help="Project root containing studio/ (default: cwd)")
    p_studio_run.add_argument(
        "--role",
        required=True,
        choices=("producer", "designer", "critic", "level_designer", "art_director"),
        help="Which role to run",
    )
    p_studio_run.add_argument("--brief", default="", help="Free-text brief for the role; uses a sensible default if omitted")
    p_studio_run.add_argument("--max-iterations", type=int, default=8, help="Cap on tool-call rounds")
    p_studio_run.add_argument(
        "--model",
        default="",
        help="Override the LLM model for this run (e.g. gemma4:latest, qwen2.5:14b-instruct). Empty = use Config defaults.",
    )
    p_studio_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Use a deterministic RehearsalLLM (no API calls). Only producer/designer/critic supported.",
    )

    p_studio_autopilot = sub.add_parser(
        "studio-autopilot",
        help="Walk the backlog and run the right role for each pending task.",
    )
    p_studio_autopilot.add_argument("--project", default=".", help="Project root containing studio/ (default: cwd)")
    p_studio_autopilot.add_argument("--max-tasks", type=int, default=5, help="Stop after this many dispatches (default: 5)")
    p_studio_autopilot.add_argument("--max-iterations", type=int, default=12, help="Cap on tool-call rounds per task")
    p_studio_autopilot.add_argument(
        "--only-role",
        action="append",
        default=[],
        help="Only dispatch tasks whose owning role matches. Repeatable.",
    )
    p_studio_autopilot.add_argument("--dry-run", action="store_true", help="Use RehearsalLLM for each dispatched role; engine-bound tasks are skipped.")
    p_studio_autopilot.add_argument("--model", default="", help="Override the LLM model used for every dispatched role.")

    p_studio_execute = sub.add_parser("studio-execute", help="Pick a backlog task and run the Worker against it (snapshot -> place -> verify -> mark done/blocked)")
    p_studio_execute.add_argument("--project", default=".", help="Project root containing studio/ (default: cwd)")
    p_studio_execute.add_argument("--task-id", required=True, help="Task id from backlog.json")
    p_studio_execute.add_argument("--extra", default="", help="Optional extra context appended to the brief")
    p_studio_execute.add_argument("--max-iterations", type=int, default=12, help="Cap on tool-call rounds (Workers usually need more than reviewers)")
    p_studio_execute.add_argument("--force", action="store_true", help="Re-run even if the task is already done or rejected")
    p_studio_execute.add_argument("--model", default="", help="Override the LLM model for this run.")

    p_studio_review = sub.add_parser("studio-review", help="Run the Producer with a standup or retro brief and write studio/reviews/<date>.md")
    p_studio_review.add_argument("--project", default=".", help="Project root containing studio/ (default: cwd)")
    p_studio_review.add_argument("--phase", choices=("morning", "evening", "adhoc"), default="adhoc", help="Which kind of review to drive")
    p_studio_review.add_argument("--extra", default="", help="Optional extra context appended to the brief")
    p_studio_review.add_argument("--max-iterations", type=int, default=8)
    p_studio_review.add_argument("--model", default="", help="Override the LLM model for this review.")
    p_studio_review.add_argument("--dry-run", action="store_true", help="Use a deterministic RehearsalLLM (no API calls)")

    p_studio_loop = sub.add_parser("studio-loop", help="Run the Producer review on a recurring cadence")
    p_studio_loop.add_argument("--project", default=".", help="Project root containing studio/ (default: cwd)")
    p_studio_loop.add_argument("--interval-hours", type=float, default=12.0, help="Hours between passes (ignored when --once)")
    p_studio_loop.add_argument("--once", action="store_true", help="Run a single pass and exit")
    p_studio_loop.add_argument("--max-passes", type=int, default=None, help="Stop after this many passes (default: unbounded)")
    p_studio_loop.add_argument("--max-iterations", type=int, default=8, help="Cap on tool-call rounds per pass")
    p_studio_loop.add_argument("--model", default="", help="Override the LLM model for the looped Producer.")
    p_chat_srv = sub.add_parser("chat-server", help="Start the TCP chat server for the Editor window")
    p_chat_srv.add_argument("--host", default="127.0.0.1")
    p_chat_srv.add_argument("--port", type=int, default=7778)
    p_chat_srv.add_argument("--use-dual-agent", action="store_true", help="Enable dual-agent mode")
    p_chat_srv.add_argument("--no-dual-agent", action="store_true", help="Force fast single-agent mode even if USE_DUAL_AGENT=true")
    p_chat_srv.add_argument("--master", default="qwen3.6:latest", help="Master model (dual-agent only; default: qwen3.6:latest, falls back if missing)")
    p_chat_srv.add_argument("--worker", default="qwen2.5:14b-instruct", help="Worker model (dual-agent only)")
    p_chat_srv.add_argument("--reader", default="qwen2.5:14b-instruct", help="Fast reader/context model (dual-agent only)")
    p_chat_srv.add_argument("--enable-memory", action="store_true", default=True, help="Enable memory system (default: true)")
    p_chat_srv.add_argument("--enable-context", action="store_true", default=True, help="Enable context management (default: true)")
    p_chat_srv.add_argument("--no-memory", dest="enable_memory", action="store_false", help="Disable memory system")
    p_chat_srv.add_argument("--no-context", dest="enable_context", action="store_false", help="Disable context management")
    p_chat_srv.add_argument("--engine", choices=["auto", "unity", "unreal"], default="auto", help="Editor context hint for tool selection")
    args = parser.parse_args()
    handlers = {
        "status": cmd_status,
        "doctor": cmd_doctor,
        "cleanup-processes": cmd_cleanup_processes,
        "chat": cmd_chat,
        "dual-chat": cmd_dual_chat,
        "unity-ping": cmd_unity_ping,
        "unreal-ping": cmd_unreal_ping,
        "install-unity-plugin": cmd_install_unity_plugin,
        "install-unreal-plugin": cmd_install_unreal_plugin,
        "migrate-unity-assets-to-unreal": cmd_migrate_unity_assets_to_unreal,
        "blender-export": cmd_blender_export,
        "chat-server": cmd_chat_server,
        "studio-init": cmd_studio_init,
        "studio-status": cmd_studio_status,
        "studio-run": cmd_studio_run,
        "studio-review": cmd_studio_review,
        "studio-loop": cmd_studio_loop,
        "studio-execute": cmd_studio_execute,
        "studio-autopilot": cmd_studio_autopilot,
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
