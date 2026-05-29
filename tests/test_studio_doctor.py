"""Phase 11 tests: studio-doctor diagnostics.

Each Check function gets one test; the integration test wires
run_diagnostics with a mocked Ollama fetch and a fake Unity bridge.
None of the checks actually hit the network.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
import urllib.error
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.core.config import Config
from unitytools.studio import (
    Check,
    StudioPaths,
    StudioState,
    Task,
    TaskStatus,
    has_failure,
    init_studio_tools,
    run_diagnostics,
)
from unitytools.studio.diagnostics import (
    _check_anthropic_key,
    _check_backlog_pressure,
    _check_config_overrides,
    _check_disk_state,
    _check_last_review,
    _check_ollama_api,
    _check_pillow,
    _check_provider,
    _check_stale_in_progress,
    _check_studio_root,
    _check_tool_registry,
    _check_unity_bridge,
)


# ──────────────────────────────────────────── helpers


def _ollama_config(model: str = "gemma4:latest") -> Config:
    return Config(api_key="", provider="ollama", ollama_host="http://127.0.0.1:11434", ollama_model=model)


def _anthropic_config(key: str = "sk-ant-test") -> Config:
    return Config(api_key=key, provider="anthropic", model="claude-sonnet-4-20250514")


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="doctor-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


class FakeUnity:
    def __init__(self, *, connect_ok=True, ping_ok=True, raise_on_connect=False):
        self._connect_ok = connect_ok
        self._ping_ok = ping_ok
        self._raise = raise_on_connect

    def connect(self, timeout=None):
        if self._raise:
            raise RuntimeError("simulated connect failure")
        return self._connect_ok

    def is_connected(self):
        return self._connect_ok

    def ping(self):
        return self._ping_ok


# ──────────────────────────────────────────── individual check tests


def test_studio_root_check_ok_and_fail() -> None:
    state, tmp = _fresh_studio()
    assert _check_studio_root(state.paths).status == "ok"
    # Empty project
    empty = StudioPaths(project_root=Path(tempfile.mkdtemp(prefix="empty-")))
    c = _check_studio_root(empty)
    assert c.status == "fail"
    assert "studio-init" in c.detail
    print("OK studio_root check")


def test_provider_check_anthropic_paths() -> None:
    # Missing key
    c = _check_provider(Config(api_key="", provider="anthropic"))
    assert c.status == "fail"
    # Bad prefix -> warn
    c = _check_provider(Config(api_key="abc-123", provider="anthropic"))
    assert c.status == "warn"
    # Good prefix -> ok
    c = _check_provider(_anthropic_config())
    assert c.status == "ok"
    print("OK provider check (anthropic)")


def test_provider_check_ollama_paths() -> None:
    c = _check_provider(_ollama_config())
    assert c.status == "ok"
    c = _check_provider(Config(api_key="", provider="ollama", ollama_model=""))
    assert c.status == "fail"
    c = _check_provider(Config(api_key="", provider="weird"))
    assert c.status == "fail"
    print("OK provider check (ollama / unknown)")


def test_ollama_api_check_uses_injected_fetch() -> None:
    """Reachable + target installed -> ok; reachable but missing -> warn;
    not reachable -> fail. No real HTTP."""

    def make_fetch(payload):
        def _f(_url):
            return payload
        return _f

    cfg = _ollama_config("gemma4:latest")
    c = _check_ollama_api(cfg, fetch=make_fetch({"models": [{"name": "gemma4:latest"}, {"name": "qwen2.5:14b"}]}))
    assert c.status == "ok"
    assert "gemma4:latest" in c.detail

    c = _check_ollama_api(cfg, fetch=make_fetch({"models": [{"name": "qwen2.5:14b"}]}))
    assert c.status == "warn"

    c = _check_ollama_api(cfg, fetch=make_fetch({"models": []}))
    assert c.status == "warn"
    assert "no models" in c.detail.lower()

    def raise_url(_):
        raise urllib.error.URLError("Connection refused")

    c = _check_ollama_api(cfg, fetch=raise_url)
    assert c.status == "fail"
    assert "unreachable" in c.detail.lower()

    # Anthropic-provider config short-circuits to ok
    c = _check_ollama_api(_anthropic_config(), fetch=make_fetch({"models": []}))
    assert c.status == "ok"
    print("OK ollama_api check happy + sad paths")


def test_anthropic_key_check() -> None:
    c = _check_anthropic_key(Config(api_key="", provider="ollama"))
    assert c.status == "warn"  # OK to not have it on ollama, but vision compare won't work
    c = _check_anthropic_key(Config(api_key="", provider="anthropic"))
    assert c.status == "fail"  # required when this is your provider
    c = _check_anthropic_key(Config(api_key="weird-prefix", provider="ollama"))
    assert c.status == "warn"
    c = _check_anthropic_key(Config(api_key="sk-ant-real", provider="ollama"))
    assert c.status == "ok"
    print("OK anthropic_key check")


def test_pillow_check_present() -> None:
    c = _check_pillow()
    # Pillow is a hard dep; should be present
    assert c.status == "ok"
    print("OK pillow check")


def test_tool_registry_check_after_studio_import() -> None:
    # _fresh_studio imports unitytools.studio, registering tools
    _fresh_studio()
    c = _check_tool_registry()
    assert c.status == "ok"
    assert "studio_*" in c.detail
    print("OK tool_registry check")


def test_disk_state_check_full_and_partial() -> None:
    state, _ = _fresh_studio()
    c = _check_disk_state(state)
    # _fresh_studio creates dirs but not the canonical files; after init the
    # CLI writes them. For this fixture they don't exist.
    assert c.status == "warn"
    assert "missing" in c.detail.lower()

    # Now write them
    state.paths.gdd.write_text("# GDD\n", encoding="utf-8")
    state.paths.art_bible.write_text("# Art Bible\n", encoding="utf-8")
    state.paths.sprint_current.write_text("# Sprint\n", encoding="utf-8")
    state.paths.backlog.write_text(json.dumps({"tasks": []}), encoding="utf-8")
    state.paths.milestones.write_text(json.dumps({"milestones": []}), encoding="utf-8")
    c = _check_disk_state(state)
    assert c.status == "ok"

    # Corrupt backlog
    state.paths.backlog.write_text("{not valid", encoding="utf-8")
    c = _check_disk_state(state)
    assert c.status == "fail"
    print("OK disk_state happy + missing + malformed")


def test_config_overrides_check() -> None:
    state, _ = _fresh_studio()
    c = _check_config_overrides(state)
    assert c.status == "ok"  # no config.json -> defaults
    assert "no config.json" in c.detail

    (state.paths.root / "config.json").write_text('{"max_role_iterations": 8}', encoding="utf-8")
    # Same as default -> warn
    c = _check_config_overrides(state)
    assert c.status == "warn"

    (state.paths.root / "config.json").write_text('{"max_role_iterations": 16}', encoding="utf-8")
    c = _check_config_overrides(state)
    assert c.status == "ok"
    assert "max_role_iterations" in c.detail
    print("OK config_overrides check")


def test_unity_bridge_check_paths() -> None:
    c = _check_unity_bridge(None)
    assert c.status == "wait"
    c = _check_unity_bridge(FakeUnity(connect_ok=False))
    assert c.status == "wait"
    c = _check_unity_bridge(FakeUnity(connect_ok=True, ping_ok=False))
    assert c.status == "warn"
    c = _check_unity_bridge(FakeUnity(connect_ok=True, ping_ok=True))
    assert c.status == "ok"
    c = _check_unity_bridge(FakeUnity(raise_on_connect=True))
    assert c.status == "fail"
    print("OK unity_bridge check across all paths")


def test_last_review_check_age_and_absence() -> None:
    state, _ = _fresh_studio()
    # No reviews yet -> warn
    c = _check_last_review(state)
    assert c.status == "warn"

    # Fresh review -> ok
    today_path = state.paths.daily_review("2026-05-11")
    today_path.parent.mkdir(parents=True, exist_ok=True)
    today_path.write_text("# 2026-05-11\n", encoding="utf-8")
    now_ts = today_path.stat().st_mtime
    c = _check_last_review(state, now=now_ts + 3600)  # 1h later
    assert c.status == "ok"

    # 5 days later -> warn (stale)
    c = _check_last_review(state, now=now_ts + 5 * 86400)
    assert c.status == "warn"
    print("OK last_review check (fresh / stale / missing)")


def test_stale_in_progress_check_no_tasks() -> None:
    state, _ = _fresh_studio()
    c = _check_stale_in_progress(state)
    assert c.status == "ok"
    assert "no tasks" in c.detail.lower()
    print("OK stale_in_progress: empty backlog -> ok")


def test_stale_in_progress_check_fresh_in_progress_is_ok() -> None:
    state, _ = _fresh_studio()
    fresh = Task(title="just started", role="worker", status=TaskStatus.IN_PROGRESS)
    fresh.created_at = fresh.updated_at = time.time() - 1 * 86400  # 1 day ago
    state.add_task(fresh)
    c = _check_stale_in_progress(state)
    assert c.status == "ok"
    print("OK stale_in_progress: fresh task -> ok")


def test_stale_in_progress_check_old_task_warns() -> None:
    state, _ = _fresh_studio()
    old = Task(title="stuck for ages", role="worker", status=TaskStatus.IN_PROGRESS)
    old.created_at = old.updated_at = time.time() - 14 * 86400  # 14 days ago
    state.add_task(old)
    # Also add a fresh one to confirm only stale ones count
    fresh = Task(title="recent", role="worker", status=TaskStatus.IN_PROGRESS)
    fresh.created_at = fresh.updated_at = time.time() - 1 * 86400
    state.add_task(fresh)
    c = _check_stale_in_progress(state)
    assert c.status == "warn"
    assert "1 task" in c.detail
    assert "studio-autopilot" in c.detail
    print("OK stale_in_progress: only counts tasks past 7d threshold")


def test_stale_in_progress_ignores_other_statuses() -> None:
    state, _ = _fresh_studio()
    # An ancient PENDING task should NOT trigger this check
    pending = Task(title="ancient pending", role="designer", status=TaskStatus.PENDING)
    pending.created_at = pending.updated_at = time.time() - 365 * 86400
    state.add_task(pending)
    c = _check_stale_in_progress(state)
    assert c.status == "ok"
    print("OK stale_in_progress: only in_progress tasks count")


def test_backlog_pressure_thresholds() -> None:
    state, _ = _fresh_studio()
    c = _check_backlog_pressure(state)
    assert c.status == "ok" and "0 tasks" in c.detail

    # Six blocked tasks -> warn
    for _ in range(6):
        state.add_task(Task(title="X", role="designer", status=TaskStatus.BLOCKED))
    c = _check_backlog_pressure(state)
    assert c.status == "warn"
    assert "blocked" in c.detail.lower()
    print("OK backlog_pressure surfaces too-many-blocked")


# ──────────────────────────────────────────── integration


def test_run_diagnostics_returns_structured_results() -> None:
    state, _ = _fresh_studio()
    cfg = _ollama_config()

    def fake_fetch(_url):
        return {"models": [{"name": "gemma4:latest"}]}

    checks = run_diagnostics(
        state,
        cfg,
        unity_bridge=FakeUnity(connect_ok=True, ping_ok=True),
        fetch_ollama=fake_fetch,
        now=time.time(),
    )
    assert isinstance(checks, list)
    assert all(isinstance(c, Check) for c in checks)
    names = [c.name for c in checks]
    # All canonical sections appear
    for expected in ("Studio root", "Provider", "Ollama API", "Pillow", "Tool registry", "Unity bridge"):
        assert expected in names
    print("OK run_diagnostics produces ordered Check list")


def test_has_failure_true_when_any_fail() -> None:
    state, _ = _fresh_studio()
    # Empty provider -> _check_provider fails
    cfg = Config(api_key="", provider="anthropic")
    checks = run_diagnostics(state, cfg)
    assert has_failure(checks)
    # Healthy ollama with mocked fetch -> no failures
    healthy_cfg = _ollama_config()
    checks = run_diagnostics(
        state,
        healthy_cfg,
        unity_bridge=FakeUnity(),
        fetch_ollama=lambda _u: {"models": [{"name": "gemma4:latest"}]},
    )
    # May still warn (e.g. disk state, last review) but no fail
    assert not has_failure(checks)
    print("OK has_failure flips on real failures only")


def run_test() -> None:
    test_studio_root_check_ok_and_fail()
    test_provider_check_anthropic_paths()
    test_provider_check_ollama_paths()
    test_ollama_api_check_uses_injected_fetch()
    test_anthropic_key_check()
    test_pillow_check_present()
    test_tool_registry_check_after_studio_import()
    test_disk_state_check_full_and_partial()
    test_config_overrides_check()
    test_unity_bridge_check_paths()
    test_last_review_check_age_and_absence()
    test_stale_in_progress_check_no_tasks()
    test_stale_in_progress_check_fresh_in_progress_is_ok()
    test_stale_in_progress_check_old_task_warns()
    test_stale_in_progress_ignores_other_statuses()
    test_backlog_pressure_thresholds()
    test_run_diagnostics_returns_structured_results()
    test_has_failure_true_when_any_fail()
    print("All Phase 11 doctor tests passed")


if __name__ == "__main__":
    run_test()
