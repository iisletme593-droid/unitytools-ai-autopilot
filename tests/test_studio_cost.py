"""Phase 33 tests: LLM cost / token observability.

Covers: estimate_cost across known + unknown models, append-then-load
round-trip, summarise aggregation (totals, by-role, by-model,
by-day), days windowing, defensive parse of corrupt log lines,
RoleRunner integration (when LLM client returns usage), Producer
allowlist access.
"""
from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    PRODUCER,
    StudioPaths,
    StudioState,
    append_cost_entry,
    cost_log_path,
    cost_summarise,
    estimate_cost,
    init_studio_tools,
    load_cost_entries,
)
from unitytools.studio.roles import RoleConfig
from unitytools.studio.runner import RoleRunner
from unitytools.studio.tools import studio_cost_summary


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="cost-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── pricing


def test_estimate_cost_claude_sonnet() -> None:
    # claude-sonnet rates are 3 in / 15 out per million
    # 1_000_000 in + 500_000 out = $3 + $7.50 = $10.50
    cost = estimate_cost("claude-sonnet-4-5", 1_000_000, 500_000)
    assert abs(cost - 10.5) < 1e-6
    print("OK estimate_cost: sonnet rates")


def test_estimate_cost_claude_haiku() -> None:
    # claude-haiku-4-5 is 1 in / 5 out per million
    cost = estimate_cost("claude-haiku-4-5", 2_000_000, 1_000_000)
    assert abs(cost - (2 + 5)) < 1e-6
    print("OK estimate_cost: haiku rates")


def test_estimate_cost_anthropic_with_timestamped_suffix() -> None:
    """Real model names look like 'claude-opus-4-5-20250929'.
    Estimator should prefix-match the family entry."""
    cost = estimate_cost("claude-opus-4-5-20250929", 1_000_000, 1_000_000)
    # opus: 15 in / 75 out per million -> 15 + 75 = 90
    assert abs(cost - 90.0) < 1e-6
    print("OK estimate_cost: prefix match for date-stamped model names")


def test_estimate_cost_local_ollama_is_zero() -> None:
    """Ollama models cost $0; we still track tokens for visibility."""
    assert estimate_cost("gemma4", 10_000_000, 5_000_000) == 0.0
    assert estimate_cost("qwen3", 100, 100) == 0.0
    print("OK estimate_cost: local models cost zero")


def test_estimate_cost_unknown_model_returns_zero() -> None:
    """A model we haven't priced isn't an error — just zero, so the
    log keeps recording the call without false alarms."""
    assert estimate_cost("some-future-model", 1000, 500) == 0.0
    assert estimate_cost("", 1000, 500) == 0.0
    print("OK estimate_cost: unknown model -> zero (no error)")


# ───────────────────────────────────────────── append / load round-trip


def test_append_and_load_round_trip() -> None:
    state, _ = _fresh_studio()
    e1 = append_cost_entry(
        state, role_id="producer", model="claude-sonnet-4-5",
        input_tokens=2500, output_tokens=800,
    )
    e2 = append_cost_entry(
        state, role_id="worker", model="gemma4",
        input_tokens=4000, output_tokens=1200,
    )
    assert e1.cost_usd > 0
    assert e2.cost_usd == 0.0  # local model
    entries = load_cost_entries(state)
    assert len(entries) == 2
    assert entries[0].role_id == "producer"
    assert entries[1].role_id == "worker"
    print("OK append + load round-trip preserves entries")


def test_append_negative_tokens_is_skipped() -> None:
    """A buggy client passing negative counts should not corrupt the log."""
    state, _ = _fresh_studio()
    entry = append_cost_entry(
        state, role_id="x", model="claude-sonnet-4-5",
        input_tokens=-100, output_tokens=50,
    )
    assert entry.input_tokens == 0
    assert entry.cost_usd == 0.0
    # Log file should be empty (nothing was appended)
    assert not cost_log_path(state).exists() or cost_log_path(state).read_text().strip() == ""
    print("OK negative tokens skip the log defensively")


def test_load_tolerates_corrupt_log_lines() -> None:
    """A truncated process or hand edit shouldn't break loading."""
    state, _ = _fresh_studio()
    path = cost_log_path(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    valid = '{"ts": 1700000000, "role_id": "p", "model": "m", "input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0}'
    path.write_text(
        valid + "\n"
        "this is not json\n"
        + valid + "\n"
        + '{"not_quite": "right"}\n'    # parses but is missing fields; defaults fill in
        + valid + "\n",
        encoding="utf-8",
    )
    entries = load_cost_entries(state)
    # The 3 valid rows survive; the malformed one is dropped; the "missing fields"
    # row parses with defaults (role_id="", model="", tokens=0).
    assert len(entries) == 4
    valid_rows = [e for e in entries if e.role_id == "p"]
    assert len(valid_rows) == 3
    print("OK load_cost_entries skips malformed JSON lines, defaults missing fields")


# ───────────────────────────────────────────── summarise


def test_summarise_aggregates_by_role_model_day() -> None:
    state, _ = _fresh_studio()
    # Seed two entries on the same day so by_day groups them
    now = time.time()
    append_cost_entry(state, role_id="producer", model="claude-sonnet-4-5",
                      input_tokens=1000, output_tokens=400, ts=now)
    append_cost_entry(state, role_id="producer", model="claude-sonnet-4-5",
                      input_tokens=500, output_tokens=200, ts=now + 1)
    append_cost_entry(state, role_id="worker", model="gemma4",
                      input_tokens=10000, output_tokens=2500, ts=now + 2)

    s = cost_summarise(state, days=0)  # all-time
    assert s["total_calls"] == 3
    assert s["total_input_tokens"] == 1000 + 500 + 10000
    assert s["total_output_tokens"] == 400 + 200 + 2500
    # by_role
    assert s["by_role"]["producer"]["calls"] == 2
    assert s["by_role"]["producer"]["input_tokens"] == 1500
    assert s["by_role"]["worker"]["calls"] == 1
    # by_model
    assert "claude-sonnet-4-5" in s["by_model"]
    assert s["by_model"]["gemma4"]["cost_usd"] == 0.0
    # by_day has at least one bucket
    assert len(s["by_day"]) >= 1
    print("OK summarise aggregates totals + by_role + by_model + by_day")


def test_summarise_windows_to_recent_days() -> None:
    """days=1 keeps only the last 24h; older rows are excluded."""
    state, _ = _fresh_studio()
    now = time.time()
    append_cost_entry(state, role_id="p", model="claude-sonnet-4-5",
                      input_tokens=100, output_tokens=50, ts=now)
    append_cost_entry(state, role_id="p", model="claude-sonnet-4-5",
                      input_tokens=200, output_tokens=100, ts=now - 86400 * 5)  # 5 days ago

    recent = cost_summarise(state, days=1)
    assert recent["total_calls"] == 1
    all_time = cost_summarise(state, days=0)
    assert all_time["total_calls"] == 2
    print("OK summarise windows to recent days; days=0 returns all")


def test_studio_cost_summary_tool_wraps_summarise() -> None:
    state, _ = _fresh_studio()
    append_cost_entry(state, role_id="p", model="claude-sonnet-4-5",
                      input_tokens=100, output_tokens=50)
    result = studio_cost_summary(days=0)
    assert result["ok"] is True
    assert result["total_calls"] == 1
    print("OK studio_cost_summary tool returns the summary dict")


# ───────────────────────────────────────────── runner integration


class FakeLLMWithUsage:
    """Returns a single text turn + usage block (Anthropic-shaped)."""

    def __init__(self, model: str = "claude-sonnet-4-5"):
        self.model = model
        self.complete_calls = 0

    def complete(self, system: str, tools: list[dict], messages: list[dict]) -> dict:
        self.complete_calls += 1
        return {
            "text": "all done",
            "tool_calls": [],
            "stop_reason": "end_turn",
            "raw_content": None,
            "usage": {
                "model": self.model,
                "input_tokens": 1234,
                "output_tokens": 56,
            },
        }


class FakeLLMNoUsage:
    """No usage block — old / test client. Cost log must NOT grow."""

    def complete(self, system: str, tools: list[dict], messages: list[dict]) -> dict:
        return {"text": "no usage here", "tool_calls": [], "stop_reason": "end_turn"}


def test_role_runner_logs_cost_when_client_returns_usage() -> None:
    state, _ = _fresh_studio()
    minimal = RoleConfig(id="minimal", name="Minimal", system_prompt="x", allowed_tools=())
    runner = RoleRunner(FakeLLMWithUsage(model="claude-sonnet-4-5"), max_iterations=1, state=state)
    runner.run(minimal, brief="please do nothing")

    entries = load_cost_entries(state)
    assert len(entries) == 1
    assert entries[0].role_id == "minimal"
    assert entries[0].model == "claude-sonnet-4-5"
    assert entries[0].input_tokens == 1234
    assert entries[0].output_tokens == 56
    assert entries[0].cost_usd > 0
    print("OK RoleRunner appends a cost row per .complete() with usage")


def test_role_runner_skips_cost_log_without_usage() -> None:
    """Backwards-compat: tests that ship without a usage block should
    not break, and the cost log should not be created."""
    state, _ = _fresh_studio()
    minimal = RoleConfig(id="minimal", name="Minimal", system_prompt="x", allowed_tools=())
    runner = RoleRunner(FakeLLMNoUsage(), max_iterations=1, state=state)
    runner.run(minimal, brief="nope")

    # Either the log file doesn't exist, or it's empty
    path = cost_log_path(state)
    assert (not path.exists()) or (path.read_text().strip() == "")
    print("OK RoleRunner silently skips logging when LLM client emits no usage block")


def test_role_runner_without_state_still_runs() -> None:
    """Existing tests construct RoleRunner without state= — that path
    must keep working."""
    minimal = RoleConfig(id="minimal", name="Minimal", system_prompt="x", allowed_tools=())
    runner = RoleRunner(FakeLLMWithUsage(), max_iterations=1)  # no state=
    result = runner.run(minimal, brief="ok")
    assert result.text == "all done"
    print("OK RoleRunner(state=None) ignores usage and runs normally")


# ───────────────────────────────────────────── Producer access


def test_producer_can_read_cost_summary() -> None:
    """The Producer cites yesterday's spend in standup / retro — give it
    read-only access to the cost summary."""
    assert "studio_cost_summary" in PRODUCER.tool_set
    # No mutation tools — Producer doesn't write to the cost log
    assert "studio_write_gdd" not in PRODUCER.tool_set
    print("OK Producer allowlist includes studio_cost_summary (read-only spend visibility)")


def run_test() -> None:
    # Pricing
    test_estimate_cost_claude_sonnet()
    test_estimate_cost_claude_haiku()
    test_estimate_cost_anthropic_with_timestamped_suffix()
    test_estimate_cost_local_ollama_is_zero()
    test_estimate_cost_unknown_model_returns_zero()
    # I/O
    test_append_and_load_round_trip()
    test_append_negative_tokens_is_skipped()
    test_load_tolerates_corrupt_log_lines()
    # Summarise
    test_summarise_aggregates_by_role_model_day()
    test_summarise_windows_to_recent_days()
    test_studio_cost_summary_tool_wraps_summarise()
    # Runner integration
    test_role_runner_logs_cost_when_client_returns_usage()
    test_role_runner_skips_cost_log_without_usage()
    test_role_runner_without_state_still_runs()
    # Role surface
    test_producer_can_read_cost_summary()
    print("All Phase 33 cost observability tests passed")


if __name__ == "__main__":
    run_test()
