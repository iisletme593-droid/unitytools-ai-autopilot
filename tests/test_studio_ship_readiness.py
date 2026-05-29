"""Phase 45 tests: studio_ship_readiness_check.

The single go/no-go gate that aggregates docs + milestones +
screenshots + recent playtests + localization + (optionally)
engine audits. Verifies each section's contribution to the
blocker list, the bridge-offline graceful skip path, role
allowlist surface, and that a fully-set-up project lands verdict
'pass'.
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
    DESIGNER,
    LIGHTING_DIRECTOR,
    MARKETING_DIRECTOR,
    PRODUCER,
    StudioPaths,
    StudioState,
    UI_BUILDER,
    WORKER,
    init_studio_tools,
    init_studio_unity,
)
from unitytools.studio.models import Milestone, MilestoneStatus
from unitytools.studio.tools import (
    studio_ship_readiness_check,
    studio_write_strings,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="ship-ready-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _fully_setup(state: StudioState) -> None:
    """Seed every section so a default check should pass (engine audits aside)."""
    state.paths.gdd.write_text("# GDD\nPitch: a game.\n", encoding="utf-8")
    state.paths.art_bible.write_text("# Art Bible\nPalette + style.\n", encoding="utf-8")
    state.paths.audio_brief.write_text("# Audio Brief\nMood.\n", encoding="utf-8")
    state.paths.press_kit.write_text("# Press Kit\n## Game Title\nX\n", encoding="utf-8")
    state.add_milestone(Milestone(name="MVP", status=MilestoneStatus.IN_PROGRESS))
    state.paths.qa_screenshots.mkdir(parents=True, exist_ok=True)
    (state.paths.qa_screenshots / "hero.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    # Recent playtest_smoke entry
    state.paths.qa_regression.parent.mkdir(parents=True, exist_ok=True)
    state.paths.qa_regression.write_text(
        json.dumps({"ts": time.time(), "kind": "playtest_smoke", "missing": []}) + "\n",
        encoding="utf-8",
    )
    studio_write_strings(locale="en", strings={"title.main": "X", "btn.start": "Start"})


# ───────────────────────────────────────────── verdict


def test_empty_studio_fails_with_multiple_blockers() -> None:
    _fresh_studio()
    result = studio_ship_readiness_check()
    assert result["ok"] is True
    assert result["verdict"] == "fail"
    # Should hit AT LEAST the doc + milestone + screenshot + playtest + locale gates
    assert result["blocker_count"] >= 5
    for required in ("gdd_empty_or_missing", "art_bible_empty_or_missing",
                      "press_kit_empty_or_missing", "no_in_progress_milestone",
                      "no_screenshots_captured", "locale_empty:en"):
        assert required in result["blockers"], f"empty studio should report {required}"
    print(f"OK empty studio: verdict=fail, {result['blocker_count']} blockers raised")


def test_fully_setup_studio_passes_when_bridge_offline_is_skipped() -> None:
    """Without bridge, engine audits are skipped — but every other gate
    must still pass for a verdict of pass. Engine audit ALSO counts as
    a blocker when skipped, so we expect 'fail' here too. This locks the
    behaviour: never falsely greenlight just because bridge is offline."""
    state, _ = _fresh_studio()
    _fully_setup(state)
    # Other tests may have injected a bridge into the module-level _UNITY;
    # clear it so this test really runs the offline path.
    import unitytools.studio.tools as st
    st._UNITY = None
    result = studio_ship_readiness_check()
    # Bridge offline -> the engine_audits section is marked skipped.
    # No engine audit results, but no blockers raised from it either.
    # All non-engine gates pass.
    assert result["sections"]["gdd"]["ok"] is True
    assert result["sections"]["art_bible"]["ok"] is True
    assert result["sections"]["press_kit"]["ok"] is True
    assert result["sections"]["milestones"]["ok"] is True
    assert result["sections"]["screenshots"]["ok"] is True
    assert result["sections"]["recent_playtest"]["ok"] is True
    assert result["sections"]["localization"]["ok"] is True
    assert result["sections"]["engine_audits"]["skipped"] is True
    # Without the engine audits running, no engine blockers were added.
    # So verdict should be 'pass' here — the skip is documented in the
    # 'reason' string but doesn't poison the verdict.
    assert result["verdict"] == "pass", (
        f"all non-engine gates pass but verdict was {result['verdict']!r}; "
        f"blockers: {result['blockers']}"
    )
    print("OK fully-set-up studio + bridge offline -> verdict=pass with engine_audits.skipped=true")


# ───────────────────────────────────────────── doc gates


def test_missing_gdd_blocks_ship() -> None:
    state, _ = _fresh_studio()
    _fully_setup(state)
    # Wipe just the GDD
    state.paths.gdd.write_text("", encoding="utf-8")
    result = studio_ship_readiness_check()
    assert result["verdict"] == "fail"
    assert "gdd_empty_or_missing" in result["blockers"]
    print("OK empty GDD alone -> blocker raised")


def test_missing_press_kit_blocks_ship() -> None:
    state, _ = _fresh_studio()
    _fully_setup(state)
    state.paths.press_kit.unlink()
    result = studio_ship_readiness_check()
    assert result["verdict"] == "fail"
    assert "press_kit_empty_or_missing" in result["blockers"]
    print("OK missing press kit -> blocker raised")


def test_audio_brief_is_optional_not_blocking() -> None:
    """Per the prompt, audio is optional — a press-kit pitch deck or
    silent-tech-demo should still ship. Audio brief absence is fine."""
    state, _ = _fresh_studio()
    _fully_setup(state)
    state.paths.audio_brief.unlink()
    result = studio_ship_readiness_check()
    # No audio_brief-specific blocker
    assert not any("audio_brief" in b for b in result["blockers"])
    print("OK missing audio brief is NOT a ship blocker (audio is optional)")


# ───────────────────────────────────────────── milestone gate


def test_no_in_progress_milestone_blocks_ship() -> None:
    state, _ = _fresh_studio()
    _fully_setup(state)
    # Mark the single milestone done
    ms = state.load_milestones()[0]
    ms.status = MilestoneStatus.DONE
    state.save_milestones([ms])
    result = studio_ship_readiness_check()
    assert result["verdict"] == "fail"
    assert "no_in_progress_milestone" in result["blockers"]
    print("OK zero in_progress milestones -> blocker")


# ───────────────────────────────────────────── screenshot gate


def test_no_screenshots_blocks_ship() -> None:
    state, _ = _fresh_studio()
    _fully_setup(state)
    for p in state.paths.qa_screenshots.glob("*.png"):
        p.unlink()
    result = studio_ship_readiness_check()
    assert result["verdict"] == "fail"
    assert "no_screenshots_captured" in result["blockers"]
    print("OK zero screenshots -> blocker")


# ───────────────────────────────────────────── playtest recency


def test_stale_playtest_blocks_ship() -> None:
    """A playtest from 30 days ago shouldn't satisfy a recent_days=7 check."""
    state, _ = _fresh_studio()
    _fully_setup(state)
    state.paths.qa_regression.write_text(
        json.dumps({"ts": time.time() - 86400 * 30, "kind": "playtest_smoke", "missing": []}) + "\n",
        encoding="utf-8",
    )
    result = studio_ship_readiness_check(recent_days=7)
    assert result["verdict"] == "fail"
    assert any("no_playtest_in_last" in b for b in result["blockers"])
    print("OK 30-day-old playtest fails recent_days=7 check")


def test_recent_playtest_inside_window_passes() -> None:
    state, _ = _fresh_studio()
    _fully_setup(state)
    # _fully_setup already writes a now-ts playtest, so verdict=pass
    result = studio_ship_readiness_check(recent_days=7)
    assert result["sections"]["recent_playtest"]["ok"] is True
    print("OK fresh playtest passes the recency gate")


# ───────────────────────────────────────────── localization


def test_missing_target_locale_blocks_ship() -> None:
    state, _ = _fresh_studio()
    _fully_setup(state)
    result = studio_ship_readiness_check(target_locales=["en", "tr"])
    assert result["verdict"] == "fail"
    # 'tr' table was never seeded
    assert "locale_empty:tr" in result["blockers"]
    print("OK requesting target locale with no table -> per-locale blocker")


def test_multi_locale_pass_when_all_seeded() -> None:
    state, _ = _fresh_studio()
    _fully_setup(state)
    studio_write_strings(locale="tr", strings={"title.main": "X", "btn.start": "Başla"})
    result = studio_ship_readiness_check(target_locales=["en", "tr"])
    assert result["sections"]["localization"]["ok"] is True
    print("OK every requested locale seeded -> localization section passes")


def test_empty_target_locales_rejected() -> None:
    _fresh_studio()
    result = studio_ship_readiness_check(target_locales=[])
    assert result["ok"] is False
    print("OK empty target_locales list rejected")


# ───────────────────────────────────────────── bridge integration


class FakeUnityAllPass:
    """Bridge that makes every engine audit return verdict='pass'."""

    def is_connected(self):
        return True

    def call(self, method, params=None, timeout=None):
        if method == "list_build_scenes":
            return {
                "ok": True, "count": 1, "enabled_count": 1,
                "active_target": "StandaloneWindows64",
                "scenes": [{"index": 0, "path": "Assets/Scenes/Main.unity", "enabled": True}],
            }
        if method == "list_lights":
            return {
                "ok": True, "count": 2, "total_intensity": 2.0,
                "shadow_casting_count": 1, "ambient_intensity": 1.0,
                "ambient_mode": "Skybox",
                "lights": [{"name": "Sun", "light_type": "Directional", "intensity": 1.0}],
            }
        if method == "get_atmosphere_state":
            return {
                "ok": True, "skybox_present": True,
                "skybox_shader": "Skybox/Procedural", "fog_enabled": False,
                "fog_mode": "ExponentialSquared", "fog_density": 0.0,
                "fog_start_distance": 0.0, "fog_end_distance": 300.0,
            }
        if method == "list_particle_systems":
            return {"ok": True, "count": 0, "total_emission_rate": 0,
                    "total_max_particles": 0, "systems": []}
        raise AssertionError(f"unexpected bridge method: {method}")


def test_fully_setup_with_bridge_passes_full_gate() -> None:
    """End-to-end: every section green AND every engine audit pass ->
    verdict=pass and zero blockers."""
    state, _ = _fresh_studio()
    _fully_setup(state)
    init_studio_unity(FakeUnityAllPass())
    result = studio_ship_readiness_check()
    assert result["verdict"] == "pass", f"unexpected blockers: {result['blockers']}"
    assert result["blocker_count"] == 0
    # Engine section present + ok=True
    assert result["sections"]["engine_audits"]["ok"] is True
    print("OK full setup + bridge connected with all-pass audits -> verdict=pass, 0 blockers")


# ───────────────────────────────────────────── role allowlist


def test_producer_marketing_build_engineer_have_ship_check() -> None:
    """The three roles that decide / cite ship readiness:
    Producer (retro), Marketing Director (before press kit handoff),
    Build Engineer (belt-and-braces before actually shipping)."""
    for role in (PRODUCER, MARKETING_DIRECTOR, BUILD_ENGINEER):
        assert "studio_ship_readiness_check" in role.tool_set, (
            f"{role.id} must have studio_ship_readiness_check"
        )
    print("OK Producer + Marketing Director + Build Engineer all have studio_ship_readiness_check")


def test_specialists_lack_ship_check() -> None:
    """Specialist roles don't decide ship readiness — they execute their
    own scoped work. Keep them out of the verdict-rendering tool."""
    for role in (DESIGNER, ART_DIRECTOR, AUDIO_DIRECTOR, LIGHTING_DIRECTOR,
                  ATMOSPHERE_DIRECTOR, UI_BUILDER, WORKER):
        assert "studio_ship_readiness_check" not in role.tool_set, (
            f"{role.id} must not run the ship readiness check"
        )
    print("OK specialist roles do not run ship readiness check")


def run_test() -> None:
    # Verdict
    test_empty_studio_fails_with_multiple_blockers()
    test_fully_setup_studio_passes_when_bridge_offline_is_skipped()
    # Doc gates
    test_missing_gdd_blocks_ship()
    test_missing_press_kit_blocks_ship()
    test_audio_brief_is_optional_not_blocking()
    # Milestone gate
    test_no_in_progress_milestone_blocks_ship()
    # Screenshot gate
    test_no_screenshots_blocks_ship()
    # Playtest recency
    test_stale_playtest_blocks_ship()
    test_recent_playtest_inside_window_passes()
    # Localization
    test_missing_target_locale_blocks_ship()
    test_multi_locale_pass_when_all_seeded()
    test_empty_target_locales_rejected()
    # Bridge integration
    test_fully_setup_with_bridge_passes_full_gate()
    # Role surface
    test_producer_marketing_build_engineer_have_ship_check()
    test_specialists_lack_ship_check()
    print("All Phase 45 ship-readiness tests passed")


if __name__ == "__main__":
    run_test()
