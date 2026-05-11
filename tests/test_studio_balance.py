"""Phase 38 tests: Game Balancer role + studio_balance_audit.

Covers: balance_audit aggregation over the regression.jsonl log
(empty / playtest data / vision compares / perf violations /
windowing), Game Balancer allowlist (doc role; reads signals,
files decisions + tasks, never mutates the scene), dispatch routing.
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
    ART_DIRECTOR,
    ATMOSPHERE_DIRECTOR,
    AUDIO_DIRECTOR,
    BUILD_ENGINEER,
    CAMERA_DIRECTOR,
    DESIGNER,
    DISPATCH_MAP,
    GAME_BALANCER,
    LIGHTING_DIRECTOR,
    MARKETING_DIRECTOR,
    MATERIAL_ARTIST,
    PHYSICS_QA,
    StudioPaths,
    StudioState,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
    init_studio_tools,
)
from unitytools.studio.tools import studio_balance_audit


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="balance-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _seed_regression(state: StudioState, entries: list[dict]) -> None:
    """Write a list of regression entries to qa/regression.jsonl."""
    state.paths.qa_regression.parent.mkdir(parents=True, exist_ok=True)
    with state.paths.qa_regression.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


# ───────────────────────────────────────────── empty + structure


def test_balance_audit_empty_log_returns_zero_signals() -> None:
    state, _ = _fresh_studio()
    result = studio_balance_audit()
    assert result["ok"] is True
    assert result["total_entries"] == 0
    assert result["playtest_smokes"] == 0
    assert result["playtest_failures"] == 0
    assert result["missing_objects"] == {}
    assert result["top_missing_objects"] == []
    assert result["avg_composition_match"] is None
    print("OK empty regression log -> zero signals across all kinds")


# ───────────────────────────────────────────── playtest aggregation


def test_balance_audit_counts_playtest_passes_and_failures() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_regression(state, [
        {"ts": now - 100, "kind": "playtest_smoke", "missing": []},
        {"ts": now - 90, "kind": "playtest_smoke", "missing": ["Hero", "Coin"]},
        {"ts": now - 80, "kind": "playtest_smoke", "missing": ["Hero"]},
        {"ts": now - 70, "kind": "playtest_smoke", "missing": ["Hero", "Door"]},
    ])
    result = studio_balance_audit()
    assert result["playtest_smokes"] == 4
    assert result["playtest_failures"] == 3   # three rounds had missing items
    assert abs(result["playtest_failure_rate"] - 0.75) < 1e-6
    print("OK playtest pass/fail counted; failure_rate computed")


def test_balance_audit_top_missing_objects_ranked_by_frequency() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_regression(state, [
        {"ts": now - 10, "kind": "playtest_smoke", "missing": ["Hero", "Coin"]},
        {"ts": now - 9, "kind": "playtest_smoke", "missing": ["Hero", "Door"]},
        {"ts": now - 8, "kind": "playtest_smoke", "missing": ["Hero"]},
        {"ts": now - 7, "kind": "playtest_smoke", "missing": ["Coin"]},
    ])
    result = studio_balance_audit()
    # Hero appeared 3x, Coin 2x, Door 1x
    top = result["top_missing_objects"]
    assert top[0]["name"] == "Hero"
    assert top[0]["missing_count"] == 3
    assert top[1]["name"] == "Coin"
    assert top[1]["missing_count"] == 2
    # max_top_offenders default is 5; we have 3 names so all surface
    assert len(top) == 3
    print("OK top_missing_objects ranked by frequency")


def test_balance_audit_caps_top_offenders() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    # 8 unique missing names, each appearing once
    _seed_regression(state, [
        {"ts": now, "kind": "playtest_smoke", "missing": [f"Obj{i}"]}
        for i in range(8)
    ])
    result = studio_balance_audit(max_top_offenders=3)
    assert len(result["top_missing_objects"]) == 3
    print("OK max_top_offenders caps the list")


# ───────────────────────────────────────────── vision compare aggregation


def test_balance_audit_averages_vision_scores() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_regression(state, [
        {"ts": now, "kind": "vision_compare", "composition_match": 0.8, "palette_match": 0.7},
        {"ts": now, "kind": "vision_compare", "composition_match": 0.6, "palette_match": 0.5},
        {"ts": now, "kind": "vision_compare", "composition_match": 0.7, "palette_match": 0.6},
    ])
    result = studio_balance_audit()
    assert result["vision_compares"] == 3
    assert abs(result["avg_composition_match"] - 0.7) < 1e-3
    assert abs(result["avg_palette_match"] - 0.6) < 1e-3
    print("OK vision compare averages computed")


# ───────────────────────────────────────────── perf + asset gen


def test_balance_audit_counts_perf_and_asset_signals() -> None:
    state, _ = _fresh_studio()
    now = time.time()
    _seed_regression(state, [
        {"ts": now, "kind": "asset_generated", "prop_type": "rock", "name": "x"},
        {"ts": now, "kind": "asset_generated", "prop_type": "crate", "name": "y"},
        {"ts": now, "kind": "perf_budget_violation", "metric": "triangles"},
        {"ts": now, "kind": "perf_budget_violation", "metric": "renderers"},
        {"ts": now, "kind": "perf_budget_violation", "metric": "triangles"},
    ])
    result = studio_balance_audit()
    assert result["asset_generations"] == 2
    assert result["perf_violations"] == 3
    assert "triangles" in result["recent_perf_violation_kinds"]
    print("OK asset_generated + perf_budget_violation kinds counted")


# ───────────────────────────────────────────── time windowing


def test_balance_audit_windows_to_recent_days() -> None:
    """Entries older than the days window are excluded."""
    state, _ = _fresh_studio()
    now = time.time()
    _seed_regression(state, [
        {"ts": now - 86400 * 30, "kind": "playtest_smoke", "missing": ["OldGhost"]},
        {"ts": now - 100, "kind": "playtest_smoke", "missing": ["Hero"]},
    ])
    # default days=7 should keep only the recent one
    result = studio_balance_audit()
    assert result["playtest_smokes"] == 1
    assert "OldGhost" not in result["missing_objects"]
    assert "Hero" in result["missing_objects"]
    # Widen to 60 days and both surface
    wide = studio_balance_audit(days=60)
    assert wide["playtest_smokes"] == 2
    print("OK time windowing excludes stale entries")


def test_balance_audit_ignores_malformed_lines() -> None:
    """A corrupt line shouldn't break the audit."""
    state, _ = _fresh_studio()
    state.paths.qa_regression.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    state.paths.qa_regression.write_text(
        json.dumps({"ts": now, "kind": "playtest_smoke", "missing": []}) + "\n"
        + "this is garbage not json\n"
        + json.dumps({"ts": now, "kind": "playtest_smoke", "missing": ["Hero"]}) + "\n",
        encoding="utf-8",
    )
    result = studio_balance_audit()
    assert result["playtest_smokes"] == 2  # garbage line skipped
    print("OK malformed lines silently skipped")


# ───────────────────────────────────────────── role allowlist


def test_game_balancer_allowlist() -> None:
    assert "studio_balance_audit" in GAME_BALANCER.tool_set
    assert "studio_recent_regressions" in GAME_BALANCER.tool_set
    assert "studio_query_archive" in GAME_BALANCER.tool_set
    assert "studio_query_decisions" in GAME_BALANCER.tool_set
    assert "studio_propose_decision" in GAME_BALANCER.tool_set
    assert "studio_add_task" in GAME_BALANCER.tool_set
    assert "studio_update_task_status" in GAME_BALANCER.tool_set
    # Reads GDD but does NOT write any doc
    assert "studio_read_gdd" in GAME_BALANCER.tool_set
    assert "studio_write_gdd" not in GAME_BALANCER.tool_set
    assert "studio_write_art_bible" not in GAME_BALANCER.tool_set
    assert "studio_write_press_kit" not in GAME_BALANCER.tool_set
    # Cannot mutate the scene
    assert "unity_create_primitive" not in GAME_BALANCER.tool_set
    assert "unity_set_position" not in GAME_BALANCER.tool_set
    assert "unity_set_light_properties" not in GAME_BALANCER.tool_set
    # Cannot run playtests (Playtester's job)
    assert "studio_playtest_smoke" not in GAME_BALANCER.tool_set
    # Cannot build / set PlayerSettings
    assert "unity_build_player" not in GAME_BALANCER.tool_set
    assert "unity_set_player_settings" not in GAME_BALANCER.tool_set
    print("OK Game Balancer allowlist: read signals + file tasks/decisions, no scene mutation, no doc writes")


def test_other_roles_lack_balance_audit() -> None:
    """studio_balance_audit is the Game Balancer's primary signal —
    nobody else needs to compute it."""
    for role in (ART_DIRECTOR, AUDIO_DIRECTOR, DESIGNER, PHYSICS_QA, WORKER,
                  LIGHTING_DIRECTOR, CAMERA_DIRECTOR, VFX_DIRECTOR, UI_BUILDER,
                  BUILD_ENGINEER, ATMOSPHERE_DIRECTOR, MATERIAL_ARTIST,
                  MARKETING_DIRECTOR):
        assert "studio_balance_audit" not in role.tool_set, (
            f"{role.id} must not run balance audits — that's Game Balancer's job"
        )
    print("OK only Game Balancer runs balance audits")


def test_game_balancer_doc_only_no_engine_no_vision() -> None:
    """Doc-only role; doesn't need Unity or vision client."""
    assert GAME_BALANCER.needs_engine is False
    assert GAME_BALANCER.needs_vision is False
    print("OK Game Balancer is engine-free + vision-free (doc-only)")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_game_balancer_to_self() -> None:
    assert DISPATCH_MAP["game_balancer"] == "game_balancer"
    print("OK DISPATCH_MAP[game_balancer] -> game_balancer")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["marketing_director"] == "marketing_director"
    assert DISPATCH_MAP["build_engineer"] == "build_engineer"
    assert DISPATCH_MAP["material_artist"] == "material_artist"
    assert DISPATCH_MAP["atmosphere_director"] == "atmosphere_director"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after game_balancer addition")


def run_test() -> None:
    # Aggregation
    test_balance_audit_empty_log_returns_zero_signals()
    test_balance_audit_counts_playtest_passes_and_failures()
    test_balance_audit_top_missing_objects_ranked_by_frequency()
    test_balance_audit_caps_top_offenders()
    test_balance_audit_averages_vision_scores()
    test_balance_audit_counts_perf_and_asset_signals()
    # Robustness
    test_balance_audit_windows_to_recent_days()
    test_balance_audit_ignores_malformed_lines()
    # Role
    test_game_balancer_allowlist()
    test_other_roles_lack_balance_audit()
    test_game_balancer_doc_only_no_engine_no_vision()
    # Dispatch
    test_dispatch_map_routes_game_balancer_to_self()
    test_existing_routes_unchanged()
    print("All Phase 38 game balancer tests passed")


if __name__ == "__main__":
    run_test()
