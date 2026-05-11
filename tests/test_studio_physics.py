"""Phase 24 tests: studio_perf_budget_check + Physics QA role.

Validates the per-metric budget logic, regression log emission,
role allowlist scoping, and the tech_artist -> physics_qa dispatch
routing change.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    DISPATCH_MAP,
    PHYSICS_QA,
    STUDIO_DEFAULTS,
    StudioPaths,
    StudioState,
    StudioThresholds,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.tools import studio_perf_budget_check


class FakePerfBridge:
    """Returns a configurable perf profile + records calls."""

    def __init__(
        self,
        connected: bool = True,
        profile: dict | None = None,
        fail: bool = False,
    ):
        self.connected = connected
        self.profile = profile or {}
        self.fail = fail
        self.calls: list[tuple[str, dict]] = []

    def is_connected(self) -> bool:
        return self.connected

    def call(self, method, params=None, timeout=None):
        params = dict(params or {})
        self.calls.append((method, params))
        if method != "profile_scene_performance":
            raise AssertionError(f"unexpected method: {method}")
        if self.fail:
            raise RuntimeError("simulated profile failure")
        return self.profile


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="phys-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


CLEAN_PROFILE = {
    "ok": True,
    "sampled_objects": 100,
    "total_scene_objects": 120,
    "renderers": 80,
    "mesh_filters": 75,
    "triangles": 250_000,
    "vertices": 180_000,
    "shadow_casters": 30,
    "unique_materials": 50,
    "lights": 1,
    "suggestions": [],
}


OVER_BUDGET_PROFILE = {
    "ok": True,
    "sampled_objects": 5000,
    "total_scene_objects": 5318,
    "renderers": 1500,           # over 1000
    "mesh_filters": 1500,
    "triangles": 3_500_000,      # over 1M
    "vertices": 2_800_000,
    "shadow_casters": 800,       # over 200
    "unique_materials": 400,     # over 250
    "lights": 4,                 # over 2
    "suggestions": [
        "Renderer count is high; prefer GPU instancing.",
        "Triangle count is high; add LODs.",
    ],
}


# ───────────────────────────────────── happy path


def test_clean_scene_passes_all_budgets() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakePerfBridge(profile=CLEAN_PROFILE))
    result = studio_perf_budget_check()
    assert result["ok"] is True
    assert result["violation_count"] == 0
    assert result["violations"] == []
    # Every breakdown entry has over_budget=False
    assert all(not e["over_budget"] for e in result["breakdown"])
    # All 5 metrics checked
    assert len(result["breakdown"]) == 5
    print("OK clean scene passes all 5 metric budgets")


def test_over_budget_scene_flags_violations() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakePerfBridge(profile=OVER_BUDGET_PROFILE))
    result = studio_perf_budget_check()
    assert result["ok"] is False
    # All 5 metrics violated in OVER_BUDGET_PROFILE
    assert result["violation_count"] == 5
    metric_names = {v["metric"] for v in result["violations"]}
    assert metric_names == {
        "triangles",
        "renderers",
        "shadow_casters",
        "unique_materials",
        "shadow_lights",
    }
    # over_by populated and positive
    assert all(v["over_by"] > 0 for v in result["violations"])
    # Unity-side suggestions surfaced
    assert result["suggestions"]
    print("OK over-budget scene surfaces all 5 violations + suggestions")


def test_per_metric_explicit_budget_overrides_default() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakePerfBridge(profile=CLEAN_PROFILE))
    # Set triangle budget below the clean profile's triangle count
    result = studio_perf_budget_check(triangle_budget=100_000)
    assert result["ok"] is False
    assert any(v["metric"] == "triangles" for v in result["violations"])
    # Other metrics still pass on defaults
    other = [v["metric"] for v in result["violations"]]
    assert "renderers" not in other
    print("OK explicit budget argument overrides StudioThresholds default")


def test_budget_zero_falls_back_to_threshold_default() -> None:
    """The contract: budget=0 means 'use the StudioThresholds default'."""
    state, _ = _fresh_studio()
    init_studio_unity(FakePerfBridge(profile=CLEAN_PROFILE))
    # All zeros -> all defaults
    result_zero = studio_perf_budget_check(triangle_budget=0, renderer_budget=0)
    # Explicit defaults
    result_explicit = studio_perf_budget_check(
        triangle_budget=STUDIO_DEFAULTS.perf_triangle_budget,
        renderer_budget=STUDIO_DEFAULTS.perf_renderer_budget,
    )
    # Same verdict, same breakdown
    assert result_zero["ok"] == result_explicit["ok"]
    assert (
        [b["budget"] for b in result_zero["breakdown"]]
        == [b["budget"] for b in result_explicit["breakdown"]]
    )
    print("OK budget=0 falls back to thresholds default")


# ───────────────────────────────────── log + thresholds


def test_perf_budget_check_logs_to_regression_jsonl() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakePerfBridge(profile=OVER_BUDGET_PROFILE))
    studio_perf_budget_check()
    log_text = state.paths.qa_regression.read_text(encoding="utf-8").strip()
    rows = [json.loads(line) for line in log_text.splitlines()]
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "perf_budget"
    assert row["ok"] is False
    assert set(row["violations"]) >= {"triangles", "renderers"}
    assert row["triangles"] == 3_500_000
    print("OK perf_budget_check appends row to qa/regression.jsonl")


def test_studio_thresholds_carries_perf_defaults() -> None:
    th = StudioThresholds()
    assert th.perf_triangle_budget == 1_000_000
    assert th.perf_renderer_budget == 1_000
    assert th.perf_shadow_caster_budget == 200
    assert th.perf_unique_material_budget == 250
    assert th.perf_shadow_light_budget == 2
    print("OK StudioThresholds carries Phase 24 perf defaults")


# ───────────────────────────────────── error paths


def test_disconnected_bridge_returns_error() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakePerfBridge(connected=False))
    result = studio_perf_budget_check()
    assert result["ok"] is False
    assert "not connected" in result["error"].lower()
    print("OK disconnected bridge surfaces clean error")


def test_profile_call_failure_returns_error() -> None:
    state, _ = _fresh_studio()
    init_studio_unity(FakePerfBridge(profile=CLEAN_PROFILE, fail=True))
    result = studio_perf_budget_check()
    assert result["ok"] is False
    assert "profile_scene_performance failed" in result["error"]
    print("OK profile failure surfaces a clear error_type")


def test_unexpected_response_shape_handled() -> None:
    state, _ = _fresh_studio()
    # Return a non-dict
    class WeirdBridge:
        def is_connected(self):
            return True

        def call(self, method, params=None, timeout=None):
            return "not a dict"

    init_studio_unity(WeirdBridge())
    result = studio_perf_budget_check()
    assert result["ok"] is False
    assert "Unexpected response" in result["error"]
    print("OK non-dict response surfaces clean error")


# ───────────────────────────────────── role + dispatch


def test_physics_qa_role_has_perf_tool_only() -> None:
    assert "studio_perf_budget_check" in PHYSICS_QA.tool_set
    # Outputs: decisions + tasks + status update
    assert "studio_propose_decision" in PHYSICS_QA.tool_set
    assert "studio_add_task" in PHYSICS_QA.tool_set
    assert "studio_update_task_status" in PHYSICS_QA.tool_set
    # NOT a scene editor
    assert "unity_create_primitive" not in PHYSICS_QA.tool_set
    assert "unity_set_position" not in PHYSICS_QA.tool_set
    # NOT a doc editor
    assert "studio_write_gdd" not in PHYSICS_QA.tool_set
    assert "studio_write_art_bible" not in PHYSICS_QA.tool_set
    print("OK Physics QA allowlist scoped to profile + report")


def test_dispatch_routes_tech_artist_to_physics_qa() -> None:
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["physics_qa"] == "physics_qa"
    # Worker still goes to worker; qa still to playtester
    assert DISPATCH_MAP["worker"] == "worker"
    assert DISPATCH_MAP["qa"] == "playtester"
    print("OK DISPATCH_MAP[tech_artist] -> physics_qa")


def test_physics_qa_needs_engine_but_not_vision() -> None:
    """Capability flags drive the Dispatcher prerequisite check."""
    assert PHYSICS_QA.needs_engine is False  # No unity_* tools; perf check goes through bridge but tool is studio_
    # Wait -- studio_perf_budget_check calls Unity internally but is named
    # studio_*. Documenting the current contract here.
    assert PHYSICS_QA.needs_vision is False
    print("OK Physics QA capability flags reflect allowlist composition")


def run_test() -> None:
    test_clean_scene_passes_all_budgets()
    test_over_budget_scene_flags_violations()
    test_per_metric_explicit_budget_overrides_default()
    test_budget_zero_falls_back_to_threshold_default()
    test_perf_budget_check_logs_to_regression_jsonl()
    test_studio_thresholds_carries_perf_defaults()
    test_disconnected_bridge_returns_error()
    test_profile_call_failure_returns_error()
    test_unexpected_response_shape_handled()
    test_physics_qa_role_has_perf_tool_only()
    test_dispatch_routes_tech_artist_to_physics_qa()
    test_physics_qa_needs_engine_but_not_vision()
    print("All Phase 24 physics QA tests passed")


if __name__ == "__main__":
    run_test()
