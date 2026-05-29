"""Phase 47 tests: Tutorial Designer role + tutorial.md doc.

Mirrors the doc-only pattern of Audio Director / Localization Lead.
Covers: path + template presence, read/write round-trip, role
allowlist isolation, dispatch routing.
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
    ATMOSPHERE_DIRECTOR,
    AUDIO_DIRECTOR,
    BUILD_ENGINEER,
    CAMERA_DIRECTOR,
    DESIGNER,
    DISPATCH_MAP,
    GAME_BALANCER,
    LIGHTING_DIRECTOR,
    LOCALIZATION_LEAD,
    MARKETING_DIRECTOR,
    MATERIAL_ARTIST,
    PHYSICS_QA,
    StudioPaths,
    StudioState,
    TUTORIAL_DESIGNER,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
    init_studio_tools,
)
from unitytools.studio.templates import starter_files
from unitytools.studio.tools import (
    studio_read_tutorial,
    studio_write_tutorial,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="tutorial-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── path + template


def test_paths_expose_tutorial() -> None:
    state, _ = _fresh_studio()
    assert state.paths.tutorial.name == "tutorial.md"
    assert state.paths.tutorial.parent == state.paths.root
    print("OK StudioPaths.tutorial -> studio/tutorial.md")


def test_starter_files_include_tutorial_template() -> None:
    files = starter_files()
    assert "tutorial.md" in files
    body = files["tutorial.md"]
    # Canonical sections the role's prompt depends on
    for section in ("Player Goal", "Controls", "Onboarding Flow",
                     "UI Surface", "Skip Path"):
        assert section in body, f"tutorial.md template missing section: {section}"
    # The template carries 3-5 beats so the role has a starting point
    for beat in ("Beat 1", "Beat 2", "Beat 3"):
        assert beat in body, f"tutorial.md template missing {beat}"
    print("OK starter_files() includes tutorial.md with canonical sections + 3 beats")


# ───────────────────────────────────────────── doc r/w round-trip


def test_read_tutorial_returns_empty_when_absent() -> None:
    _fresh_studio()
    result = studio_read_tutorial()
    assert result["ok"] is True
    assert result["content"] == ""
    print("OK read_tutorial: empty when file absent")


def test_write_then_read_tutorial_round_trip() -> None:
    state, _ = _fresh_studio()
    body = (
        "# Tutorial\n\n## Player Goal\nDodge obstacles, hit 30 coins.\n\n"
        "## Controls\n- A/D: switch lanes\n- Esc: pause\n\n"
        "## Onboarding Flow\n### Beat 1 — Hook\nThe player sees the camera "
        "race forward over the lane band.\n"
    )
    write_result = studio_write_tutorial(content=body)
    assert write_result["ok"] is True
    assert write_result["path"] == str(state.paths.tutorial)
    assert state.paths.tutorial.exists()

    read_result = studio_read_tutorial()
    assert "Dodge obstacles" in read_result["content"]
    assert "switch lanes" in read_result["content"]
    print("OK tutorial write then read round-trips")


# ───────────────────────────────────────────── role allowlist


def test_tutorial_designer_allowlist() -> None:
    """The role reads the tutorial + GDD and writes the tutorial; it
    files follow-up tasks for UI Builder + Localization but cannot
    write any other doc or mutate the scene."""
    assert "studio_read_tutorial" in TUTORIAL_DESIGNER.tool_set
    assert "studio_write_tutorial" in TUTORIAL_DESIGNER.tool_set
    assert "studio_read_gdd" in TUTORIAL_DESIGNER.tool_set
    # Lifecycle + escalation
    assert "studio_update_task_status" in TUTORIAL_DESIGNER.tool_set
    assert "studio_add_task" in TUTORIAL_DESIGNER.tool_set
    assert "studio_propose_decision" in TUTORIAL_DESIGNER.tool_set
    # Cannot write any OTHER doc
    assert "studio_write_gdd" not in TUTORIAL_DESIGNER.tool_set
    assert "studio_write_art_bible" not in TUTORIAL_DESIGNER.tool_set
    assert "studio_write_audio_brief" not in TUTORIAL_DESIGNER.tool_set
    assert "studio_write_press_kit" not in TUTORIAL_DESIGNER.tool_set
    # Cannot seed string tables (Localization Lead handles that downstream)
    assert "studio_write_strings" not in TUTORIAL_DESIGNER.tool_set
    # Cannot mutate scene
    assert "unity_create_primitive" not in TUTORIAL_DESIGNER.tool_set
    assert "unity_create_ui_text" not in TUTORIAL_DESIGNER.tool_set
    assert "unity_attach_behaviour" not in TUTORIAL_DESIGNER.tool_set
    # Cannot run play mode / build
    assert "studio_playtest_smoke" not in TUTORIAL_DESIGNER.tool_set
    assert "unity_build_player" not in TUTORIAL_DESIGNER.tool_set
    print("OK Tutorial Designer allowlist: tutorial r/w + GDD r + tasks/decisions, nothing else")


def test_other_roles_lack_tutorial_write() -> None:
    """Only Tutorial Designer writes tutorial.md."""
    for role in (ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR,
                  BUILD_ENGINEER, CAMERA_DIRECTOR, DESIGNER,
                  GAME_BALANCER, LIGHTING_DIRECTOR, LOCALIZATION_LEAD,
                  MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
                  UI_BUILDER, VFX_DIRECTOR, WORKER):
        assert "studio_write_tutorial" not in role.tool_set, (
            f"{role.id} must not write the tutorial"
        )
    print("OK only Tutorial Designer writes the tutorial")


def test_tutorial_designer_doc_only_no_engine() -> None:
    assert TUTORIAL_DESIGNER.needs_engine is False
    assert TUTORIAL_DESIGNER.needs_vision is False
    print("OK Tutorial Designer is engine-free + vision-free (doc-only)")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_tutorial_designer_to_self() -> None:
    assert DISPATCH_MAP["tutorial_designer"] == "tutorial_designer"
    print("OK DISPATCH_MAP[tutorial_designer] -> tutorial_designer")


def test_existing_routes_unchanged() -> None:
    """Adding the new role must not disturb the other 20."""
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["audio_director"] == "audio_director"
    assert DISPATCH_MAP["localization_lead"] == "localization_lead"
    assert DISPATCH_MAP["marketing_director"] == "marketing_director"
    assert DISPATCH_MAP["build_engineer"] == "build_engineer"
    assert DISPATCH_MAP["qa"] == "playtester"
    assert DISPATCH_MAP["tech_artist"] == "physics_qa"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after tutorial_designer addition")


def test_tutorial_designer_in_roles_validation_tuple() -> None:
    """Bug fix coverage: the ROLES tuple in models.py is what
    studio_add_task validates against. tutorial_designer must be
    listed there or scaffolders / Producer add_task calls will be
    rejected."""
    from unitytools.studio.models import ROLES
    assert "tutorial_designer" in ROLES, (
        "tutorial_designer must be in ROLES tuple so studio_add_task accepts it"
    )
    print("OK tutorial_designer is in ROLES validation tuple")


def run_test() -> None:
    # Path + template
    test_paths_expose_tutorial()
    test_starter_files_include_tutorial_template()
    # Doc r/w
    test_read_tutorial_returns_empty_when_absent()
    test_write_then_read_tutorial_round_trip()
    # Role
    test_tutorial_designer_allowlist()
    test_other_roles_lack_tutorial_write()
    test_tutorial_designer_doc_only_no_engine()
    # Dispatch
    test_dispatch_map_routes_tutorial_designer_to_self()
    test_existing_routes_unchanged()
    test_tutorial_designer_in_roles_validation_tuple()
    print("All Phase 47 tutorial designer tests passed")


if __name__ == "__main__":
    run_test()
