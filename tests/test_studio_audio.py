"""Phase 26 tests: Audio Director role + audio brief tools.

Doc-only pattern mirroring the Art Director: read/write a markdown
document, propose decisions, file follow-up tasks. No engine touch.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    ART_DIRECTOR,
    AUDIO_DIRECTOR,
    DISPATCH_MAP,
    DESIGNER,
    StudioPaths,
    StudioState,
    init_studio_tools,
)
from unitytools.studio.templates import starter_files
from unitytools.studio.tools import (
    studio_read_audio_brief,
    studio_write_audio_brief,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="audio-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ─────────────────────────────────────────── paths + templates


def test_paths_expose_audio_brief() -> None:
    state, _ = _fresh_studio()
    assert state.paths.audio_brief.name == "audio_brief.md"
    assert state.paths.audio_brief.parent == state.paths.root
    print("OK StudioPaths.audio_brief = studio/audio_brief.md")


def test_starter_files_include_audio_brief_template() -> None:
    files = starter_files()
    assert "audio_brief.md" in files
    body = files["audio_brief.md"]
    # Template has the canonical sections
    assert "Audio Brief" in body
    assert "Mood Tanımı" in body or "Mood Tan" in body
    assert "Sonik Palet" in body
    assert "Referans Parça" in body
    print("OK starter_files() includes audio_brief.md with canonical sections")


# ─────────────────────────────────────────── tool round-trip


def test_read_audio_brief_returns_empty_when_absent() -> None:
    state, _ = _fresh_studio()
    result = studio_read_audio_brief()
    assert result["ok"] is True
    assert result["content"] == ""
    print("OK read_audio_brief: empty when file absent")


def test_write_then_read_audio_brief_round_trip() -> None:
    state, _ = _fresh_studio()
    body = "# Audio Brief\n\nCold synth ambient. 48 kHz / 24 bit.\n"
    write_result = studio_write_audio_brief(content=body)
    assert write_result["ok"] is True
    assert write_result["path"] == str(state.paths.audio_brief)
    assert state.paths.audio_brief.exists()

    read_result = studio_read_audio_brief()
    assert read_result["ok"] is True
    assert "Cold synth ambient" in read_result["content"]
    print("OK audio brief write then read round-trips")


# ─────────────────────────────────────────── role allowlist


def test_audio_director_owns_audio_brief_writes() -> None:
    assert "studio_write_audio_brief" in AUDIO_DIRECTOR.tool_set
    assert "studio_read_audio_brief" in AUDIO_DIRECTOR.tool_set
    # MUST NOT touch GDD or Art Bible
    assert "studio_write_gdd" not in AUDIO_DIRECTOR.tool_set
    assert "studio_write_art_bible" not in AUDIO_DIRECTOR.tool_set
    # MUST NOT touch the scene
    assert "unity_create_primitive" not in AUDIO_DIRECTOR.tool_set
    assert "studio_capture_screenshot" not in AUDIO_DIRECTOR.tool_set
    # Lifecycle + decisions surface
    assert "studio_update_task_status" in AUDIO_DIRECTOR.tool_set
    assert "studio_propose_decision" in AUDIO_DIRECTOR.tool_set
    print("OK Audio Director allowlist: brief r/w + decisions + lifecycle, no engine, no other docs")


def test_other_roles_cannot_write_audio_brief() -> None:
    """Only the Audio Director writes the brief. Art Director / Designer
    explicitly do NOT have the tool."""
    for role in (DESIGNER, ART_DIRECTOR):
        assert "studio_write_audio_brief" not in role.tool_set, f"{role.id} must not write audio brief"
    print("OK only Audio Director writes the audio brief")


def test_audio_director_has_no_engine_or_vision_requirements() -> None:
    """Doc-only role; runs without Unity or vision client."""
    assert AUDIO_DIRECTOR.needs_engine is False
    assert AUDIO_DIRECTOR.needs_vision is False
    print("OK Audio Director is engine-free + vision-free (doc-only)")


# ─────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_audio_director_to_self() -> None:
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    print("OK DISPATCH_MAP[audio_director] -> audio_director")


def test_existing_routes_unchanged() -> None:
    """Adding the new role must not disturb earlier dispatch rules."""
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["art_director"] == "art_director"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after audio_director addition")


def run_test() -> None:
    test_paths_expose_audio_brief()
    test_starter_files_include_audio_brief_template()
    test_read_audio_brief_returns_empty_when_absent()
    test_write_then_read_audio_brief_round_trip()
    test_audio_director_owns_audio_brief_writes()
    test_other_roles_cannot_write_audio_brief()
    test_audio_director_has_no_engine_or_vision_requirements()
    test_dispatch_map_routes_audio_director_to_self()
    test_existing_routes_unchanged()
    print("All Phase 26 audio director tests passed")


if __name__ == "__main__":
    run_test()
