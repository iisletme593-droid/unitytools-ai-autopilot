"""Phase 58 tests: studio_dashboard.

The dashboard aggregates 7 sections (counts / ship readiness /
internal consistency / cost / balance / recent regressions /
milestones in flight) into one report. Verifies:
- Each section is present in the output
- Headline computation: 'green' when no blockers vs 'blockers' when
  ship readiness fails / consistency drifts / failure rate is high
- Markdown report is well-formed (sections + counts + blockers
  visible)
- save_report=True writes to studio/reviews/dashboard_<date>.md
- Producer + Critic have it; specialists don't
- Input validation (days bound)
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    CRITIC,
    PRODUCER,
    StudioPaths,
    StudioState,
    init_studio_tools,
)
from unitytools.studio.models import Milestone, MilestoneStatus
from unitytools.studio.tools import studio_dashboard, studio_write_strings


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="dashboard-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _make_ship_ready(state: StudioState) -> None:
    """Seed every ship-readiness gate so the dashboard's headline is green."""
    state.paths.gdd.write_text("# GDD\nThe pitch.\n", encoding="utf-8")
    state.paths.art_bible.write_text("# Art Bible\n", encoding="utf-8")
    state.paths.press_kit.write_text("# Press\n## Game Title\nX\n", encoding="utf-8")
    state.add_milestone(Milestone(name="MVP", status=MilestoneStatus.IN_PROGRESS))
    (state.paths.qa_screenshots / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    # Fresh playtest
    import json
    state.paths.qa_regression.write_text(
        json.dumps({"ts": time.time(), "kind": "playtest_smoke", "missing": []}) + "\n",
        encoding="utf-8",
    )
    studio_write_strings(locale="en", strings={"btn.start": "Start"})
    # Clear any lingering Unity bridge so engine audits are skipped cleanly
    import unitytools.studio.tools as st
    st._UNITY = None


# ───────────────────────────────────────────── verdict + sections


def test_dashboard_empty_studio_reports_blockers_headline() -> None:
    _fresh_studio()
    r = studio_dashboard(days=7)
    assert r["ok"] is True
    assert r["headline"] == "blockers"
    # The ship readiness fail alone surfaces as a blocker tag
    assert "ship_readiness_fail" in r["blockers"]
    print("OK empty studio dashboard -> headline=blockers (7 doc/screenshot/locale gates open)")


def test_dashboard_seven_sections_always_present() -> None:
    _fresh_studio()
    r = studio_dashboard(days=7)
    expected = {"counts", "ship_readiness", "internal_consistency", "cost",
                 "balance", "recent_regressions", "milestones_in_flight"}
    missing = expected - set(r["sections"].keys())
    assert not missing, f"dashboard sections missing: {missing}"
    print(f"OK dashboard always emits all 7 sections: {sorted(expected)}")


def test_dashboard_fully_ready_studio_reports_green_headline() -> None:
    """If every gate passes (engine audits skipped cleanly when bridge
    offline), the headline goes green."""
    state, _ = _fresh_studio()
    _make_ship_ready(state)
    r = studio_dashboard(days=7)
    assert r["sections"]["ship_readiness"]["verdict"] == "pass", (
        f"expected ship_readiness pass; blockers: "
        f"{r['sections']['ship_readiness'].get('blockers')}"
    )
    assert r["sections"]["internal_consistency"]["verdict"] == "pass"
    assert r["headline"] == "green", f"expected green; got blockers {r['blockers']}"
    print("OK fully-set-up studio + bridge offline -> headline=green")


# ───────────────────────────────────────────── balance failure rate gate


def test_dashboard_flags_high_playtest_failure_rate() -> None:
    """When balance_audit reports failure_rate > 0.5, the dashboard
    surfaces a 'playtest_failure_rate_high:<value>' blocker."""
    state, _ = _fresh_studio()
    _make_ship_ready(state)
    # Overwrite the regression log with 4 failed playtests + 1 pass
    import json
    now = time.time()
    rows = [
        {"ts": now - 100, "kind": "playtest_smoke", "missing": []},   # pass
        {"ts": now - 90, "kind": "playtest_smoke", "missing": ["Hero"]},
        {"ts": now - 80, "kind": "playtest_smoke", "missing": ["Hero"]},
        {"ts": now - 70, "kind": "playtest_smoke", "missing": ["Hero"]},
        {"ts": now - 60, "kind": "playtest_smoke", "missing": ["Hero"]},
    ]
    with state.paths.qa_regression.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    r = studio_dashboard(days=7)
    # 4/5 = 0.8 failure rate
    assert any("playtest_failure_rate_high" in b for b in r["blockers"])
    print("OK 80% playtest failure rate surfaces as dashboard blocker")


# ───────────────────────────────────────────── markdown


def test_dashboard_markdown_contains_every_section_header() -> None:
    state, _ = _fresh_studio()
    _make_ship_ready(state)
    r = studio_dashboard(days=7)
    md = r["markdown"]
    for header in ("# Studio Dashboard",
                    "## Counts", "## Ship Readiness",
                    "## Internal Consistency", "## Cost",
                    "## Balance"):
        assert header in md, f"markdown missing header: {header!r}"
    # Window phrase
    assert "last 7 day" in md or "last 7d" in md.lower()
    print("OK markdown report contains all section headers + window")


def test_dashboard_markdown_lists_ship_readiness_blockers() -> None:
    _fresh_studio()
    r = studio_dashboard(days=7)
    md = r["markdown"]
    # 7 blockers on an empty studio should all appear (or be capped at 8)
    for blocker_name in ("gdd_empty_or_missing", "no_screenshots_captured",
                          "locale_empty:en"):
        assert blocker_name in md, f"markdown should list blocker: {blocker_name}"
    print("OK markdown surfaces ship readiness blockers verbatim")


# ───────────────────────────────────────────── save report


def test_dashboard_save_report_writes_markdown_to_reviews() -> None:
    state, _ = _fresh_studio()
    r = studio_dashboard(days=7, save_report=True)
    assert r["saved_path"] is not None
    saved = Path(r["saved_path"])
    assert saved.exists()
    assert saved.parent == state.paths.reviews
    assert saved.name.startswith("dashboard_")
    assert saved.name.endswith(".md")
    # Content matches what we returned in-memory
    assert saved.read_text(encoding="utf-8") == r["markdown"]
    print(f"OK save_report=True writes studio/reviews/{saved.name}")


def test_dashboard_save_false_does_not_write_file() -> None:
    state, _ = _fresh_studio()
    r = studio_dashboard(days=7, save_report=False)
    assert r["saved_path"] is None
    # No dashboard_* file should exist
    assert not any(state.paths.reviews.glob("dashboard_*.md"))
    print("OK save_report=False is a pure read; no file written")


# ───────────────────────────────────────────── input validation


def test_dashboard_rejects_zero_or_negative_days() -> None:
    _fresh_studio()
    for bad in (0, -1, -7):
        r = studio_dashboard(days=bad)
        assert r["ok"] is False
        assert "days" in r["error"]
    print("OK days<=0 rejected")


def test_dashboard_rejects_excessive_days() -> None:
    _fresh_studio()
    r = studio_dashboard(days=365)
    assert r["ok"] is False
    assert "days" in r["error"]
    print("OK days>90 rejected (cap to keep aggregates fast)")


# ───────────────────────────────────────────── role surface


def test_producer_and_critic_have_dashboard() -> None:
    assert "studio_dashboard" in PRODUCER.tool_set
    assert "studio_dashboard" in CRITIC.tool_set
    print("OK Producer + Critic both have studio_dashboard")


def test_specialists_do_not_have_dashboard() -> None:
    from unitytools.studio import (
        ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR, BUILD_ENGINEER,
        CAMERA_DIRECTOR, DESIGNER, GAME_BALANCER, LIGHTING_DIRECTOR,
        LOCALIZATION_LEAD, MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
        SCENE_DIRECTOR, STORYTELLER, TUTORIAL_DESIGNER, UI_BUILDER,
        VFX_DIRECTOR, WORKER, ACHIEVEMENT_DESIGNER,
    )
    for role in (ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR,
                  BUILD_ENGINEER, CAMERA_DIRECTOR, DESIGNER, GAME_BALANCER,
                  LIGHTING_DIRECTOR, LOCALIZATION_LEAD, MARKETING_DIRECTOR,
                  MATERIAL_ARTIST, PHYSICS_QA, SCENE_DIRECTOR, STORYTELLER,
                  TUTORIAL_DESIGNER, UI_BUILDER, VFX_DIRECTOR, WORKER,
                  ACHIEVEMENT_DESIGNER):
        assert "studio_dashboard" not in role.tool_set, (
            f"{role.id} must not run the dashboard"
        )
    print("OK 19 specialist roles do not run studio_dashboard")


def run_test() -> None:
    # Verdict + sections
    test_dashboard_empty_studio_reports_blockers_headline()
    test_dashboard_seven_sections_always_present()
    test_dashboard_fully_ready_studio_reports_green_headline()
    # Balance gate
    test_dashboard_flags_high_playtest_failure_rate()
    # Markdown
    test_dashboard_markdown_contains_every_section_header()
    test_dashboard_markdown_lists_ship_readiness_blockers()
    # Save
    test_dashboard_save_report_writes_markdown_to_reviews()
    test_dashboard_save_false_does_not_write_file()
    # Validation
    test_dashboard_rejects_zero_or_negative_days()
    test_dashboard_rejects_excessive_days()
    # Role surface
    test_producer_and_critic_have_dashboard()
    test_specialists_do_not_have_dashboard()
    print("All Phase 58 studio_dashboard tests passed")


if __name__ == "__main__":
    run_test()
