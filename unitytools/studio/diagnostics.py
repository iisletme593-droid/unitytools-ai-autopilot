"""Studio diagnostics — `unitytools studio-doctor` data layer.

Each check returns a Check(name, status, detail) and runs independently;
none of them crash on a failure path. The CLI iterates the results and
prints them in order. Exit code policy: any "fail" status -> exit 1;
"warn" / "wait" / "ok" all -> exit 0 so cron / CI can surface real
breakage without thrashing on transient editor-not-connected states.
"""
from __future__ import annotations

import dataclasses
import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Literal, Optional

from ..core.config import Config
from .config import STUDIO_DEFAULTS
from .paths import StudioPaths
from .state import StudioState

logger = logging.getLogger(__name__)


CheckStatus = Literal["ok", "warn", "fail", "wait"]


@dataclass
class Check:
    name: str
    status: CheckStatus
    detail: str = ""

    @property
    def is_failure(self) -> bool:
        return self.status == "fail"


# ─── individual checks ─────────────────────────────────────────────────


def _check_studio_root(paths: StudioPaths) -> Check:
    if paths.exists():
        return Check("Studio root", "ok", str(paths.root))
    return Check("Studio root", "fail", f"missing -- run `unitytools studio-init --project {paths.project_root}`")


def _check_provider(config: Config) -> Check:
    if config.provider == "anthropic":
        if not config.api_key:
            return Check("Provider", "fail", "anthropic but ANTHROPIC_API_KEY missing")
        if not config.api_key.startswith("sk-ant-"):
            return Check("Provider", "warn", "API key does not start with sk-ant-")
        return Check("Provider", "ok", f"anthropic, model {config.model}")
    if config.provider == "ollama":
        if not config.ollama_model:
            return Check("Provider", "fail", "ollama but OLLAMA_MODEL is empty")
        return Check("Provider", "ok", f"ollama, model {config.ollama_model}")
    return Check("Provider", "fail", f"unknown provider {config.provider!r}")


def _check_ollama_api(config: Config, fetch=None) -> Check:
    """Probe the Ollama tags endpoint. `fetch` injectable for tests."""
    if config.provider != "ollama":
        return Check("Ollama API", "ok", "(not configured as provider)")
    fetch = fetch or _default_fetch
    url = f"{config.ollama_host.rstrip('/')}/api/tags"
    try:
        data = fetch(url)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
        return Check("Ollama API", "fail", f"unreachable at {config.ollama_host}: {exc}")
    except Exception as exc:  # noqa: BLE001
        return Check("Ollama API", "fail", f"error: {exc}")
    models = [m.get("name", "") for m in data.get("models", []) if isinstance(m, dict)]
    if not models:
        return Check("Ollama API", "warn", "reachable but no models installed")
    if config.ollama_model in models:
        return Check(
            "Ollama API",
            "ok",
            f"reachable, target {config.ollama_model!r} installed ({len(models)} total)",
        )
    return Check(
        "Ollama API",
        "warn",
        f"reachable but {config.ollama_model!r} not installed (have: {', '.join(models[:4])})",
    )


def _default_fetch(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=3) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _check_anthropic_key(config: Config) -> Check:
    if config.provider == "anthropic" and not config.api_key:
        return Check("Anthropic key", "fail", "missing -- studio cannot run")
    if not config.api_key:
        return Check(
            "Anthropic key",
            "warn",
            "absent -- studio_compare_to_reference will return errors",
        )
    if not config.api_key.startswith("sk-ant-"):
        return Check("Anthropic key", "warn", "present but unusual prefix")
    return Check("Anthropic key", "ok", "present (sk-ant-***)")


def _check_pillow() -> Check:
    try:
        from PIL import Image
    except ImportError:
        return Check(
            "Pillow",
            "warn",
            "missing -- studio_visual_regression_check unavailable. pip install Pillow",
        )
    return Check("Pillow", "ok", getattr(Image, "__version__", "installed"))


def _check_tool_registry() -> Check:
    from ..core.tool_registry import get_all_tools

    tools = get_all_tools()
    studio_count = sum(1 for t in tools if t.name.startswith("studio_"))
    if studio_count == 0:
        return Check(
            "Tool registry",
            "fail",
            "no studio_* tools registered -- import unitytools.studio before running",
        )
    return Check(
        "Tool registry",
        "ok",
        f"{len(tools)} total, {studio_count} studio_*",
    )


def _check_disk_state(state: StudioState) -> Check:
    paths = state.paths
    canonical = (
        ("gdd.md", paths.gdd),
        ("art_bible.md", paths.art_bible),
        ("sprint_current.md", paths.sprint_current),
        ("backlog.json", paths.backlog),
        ("milestones.json", paths.milestones),
    )
    missing = [name for name, p in canonical if not p.exists()]
    if missing:
        return Check("Disk state", "warn", f"missing: {', '.join(missing)}")
    # Sanity: backlog and milestones are valid JSON
    try:
        json.loads(paths.backlog.read_text(encoding="utf-8") or "{}")
        json.loads(paths.milestones.read_text(encoding="utf-8") or "{}")
    except json.JSONDecodeError as exc:
        return Check("Disk state", "fail", f"backlog or milestones malformed: {exc}")
    return Check("Disk state", "ok", "all canonical files present and parseable")


def _check_config_overrides(state: StudioState) -> Check:
    config_file = state.paths.root / "config.json"
    if not config_file.exists():
        return Check("Config overrides", "ok", "no config.json (using defaults)")
    thresh = state.thresholds
    diff = [
        f.name
        for f in dataclasses.fields(thresh)
        if getattr(thresh, f.name) != getattr(STUDIO_DEFAULTS, f.name)
    ]
    if not diff:
        return Check(
            "Config overrides",
            "warn",
            "config.json present but no effective overrides (typo? unknown keys?)",
        )
    return Check("Config overrides", "ok", f"{len(diff)} override(s): {', '.join(diff)}")


def _check_unity_bridge(unity_bridge: Optional[Any]) -> Check:
    if unity_bridge is None:
        return Check("Unity bridge", "wait", "not initialised (engine roles will skip)")
    try:
        connected = unity_bridge.connect(timeout=2.0) if hasattr(unity_bridge, "connect") else unity_bridge.is_connected()
    except Exception as exc:  # noqa: BLE001
        return Check("Unity bridge", "fail", f"connect raised: {exc}")
    if not connected:
        return Check("Unity bridge", "wait", "Editor not connected -- engine tasks will skip")
    try:
        pong = unity_bridge.ping() if hasattr(unity_bridge, "ping") else True
    except Exception as exc:  # noqa: BLE001
        return Check("Unity bridge", "warn", f"connected but ping raised: {exc}")
    if not pong:
        return Check("Unity bridge", "warn", "connected but ping failed")
    return Check("Unity bridge", "ok", "connected and responsive")


def _check_last_review(state: StudioState, now: Optional[float] = None) -> Check:
    now = now if now is not None else time.time()
    reviews_dir = state.paths.reviews
    if not reviews_dir.is_dir():
        return Check("Last review", "warn", "no reviews/ folder yet")
    files = sorted(p for p in reviews_dir.glob("*.md") if p.is_file())
    if not files:
        return Check("Last review", "warn", "no reviews yet -- run `unitytools studio-review --phase morning`")
    latest = files[-1]
    age_days = (now - latest.stat().st_mtime) / 86400.0
    if age_days < 2.0:
        return Check("Last review", "ok", f"{latest.name} ({age_days:.1f}d ago)")
    if age_days < 7.0:
        return Check("Last review", "warn", f"{latest.name} ({age_days:.1f}d ago) -- stale")
    return Check("Last review", "warn", f"{latest.name} ({age_days:.0f}d ago) -- very stale")


def _check_archivable_tasks(state: StudioState, now: Optional[float] = None, age_days: float = 30.0) -> Check:
    """Suggest running studio-archive when many old done tasks linger."""
    from .models import TaskStatus

    now = now if now is not None else time.time()
    cutoff = now - age_days * 86400.0
    archivable = 0
    for t in state.load_tasks():
        if t.status in (TaskStatus.DONE, TaskStatus.REJECTED):
            ts = t.updated_at or t.created_at or 0.0
            if ts and ts < cutoff:
                archivable += 1
    if archivable == 0:
        return Check("Archivable tasks", "ok", "0 stale done/rejected in backlog")
    if archivable < 20:
        return Check("Archivable tasks", "ok", f"{archivable} could be archived (no rush)")
    return Check(
        "Archivable tasks",
        "warn",
        f"{archivable} done/rejected tasks older than {age_days:g}d -- run `unitytools studio-archive`",
    )


def _check_backlog_pressure(state: StudioState) -> Check:
    """Surface a warning when too many tasks pile up in any single status."""
    from .models import TaskStatus

    tasks = state.load_tasks()
    if not tasks:
        return Check("Backlog", "ok", "0 tasks (fresh project)")
    by_status: dict[str, int] = {}
    for t in tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
    pending = by_status.get(TaskStatus.PENDING.value, 0)
    blocked = by_status.get(TaskStatus.BLOCKED.value, 0)
    review = by_status.get(TaskStatus.REVIEW.value, 0)
    parts = [f"{k}={v}" for k, v in sorted(by_status.items())]
    detail = ", ".join(parts)
    if blocked > 5:
        return Check("Backlog", "warn", f"{blocked} blocked tasks need attention ({detail})")
    if pending > 25:
        return Check("Backlog", "warn", f"{pending} pending tasks -- producer is overproducing ({detail})")
    if review > 10:
        return Check("Backlog", "warn", f"{review} tasks awaiting review ({detail})")
    return Check("Backlog", "ok", detail)


# ─── main runner ───────────────────────────────────────────────────────


def run_diagnostics(
    state: StudioState,
    config: Config,
    unity_bridge: Optional[Any] = None,
    *,
    fetch_ollama=None,
    now: Optional[float] = None,
) -> list[Check]:
    """Run all checks in order. Returns a list[Check]; never raises."""
    checks: list[Check] = []
    checks.append(_check_studio_root(state.paths))
    checks.append(_check_provider(config))
    checks.append(_check_ollama_api(config, fetch=fetch_ollama))
    checks.append(_check_anthropic_key(config))
    checks.append(_check_pillow())
    checks.append(_check_tool_registry())
    checks.append(_check_disk_state(state))
    checks.append(_check_config_overrides(state))
    checks.append(_check_unity_bridge(unity_bridge))
    checks.append(_check_last_review(state, now=now))
    checks.append(_check_backlog_pressure(state))
    checks.append(_check_archivable_tasks(state, now=now))
    return checks


def has_failure(checks: list[Check]) -> bool:
    return any(c.is_failure for c in checks)
