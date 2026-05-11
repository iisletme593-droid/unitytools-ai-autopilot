"""Phase 51 tests: Achievement Designer role + achievements.md doc.

Doc-only pattern. Verifies path + template, read/write round-trip,
role allowlist isolation, dispatch routing. Also verifies that the
Worker can READ the achievements roster (so it knows which
Achievement components to attach).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    ACHIEVEMENT_DESIGNER,
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
    SCENE_DIRECTOR,
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
    studio_read_achievements,
    studio_write_achievements,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="achievement-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── path + template


def test_paths_expose_achievements() -> None:
    state, _ = _fresh_studio()
    assert state.paths.achievements.name == "achievements.md"
    assert state.paths.achievements.parent == state.paths.root
    print("OK StudioPaths.achievements -> studio/achievements.md")


def test_starter_files_include_achievements_template() -> None:
    files = starter_files()
    assert "achievements.md" in files
    body = files["achievements.md"]
    # Canonical sections
    for section in ("Roster", "Design Rules", "Trigger Kinds",
                     "UI Surface", "Persistence"):
        assert section in body, f"achievements.md missing section: {section}"
    # The 3 trigger kinds the C# enum supports (names must match exactly
    # since the Worker passes them through to AttachBehaviour reflection)
    for kind in ("ScoreAtLeast", "LivesRemainingAtMost", "GameOver"):
        assert kind in body, f"template missing trigger kind: {kind}"
    # Roster has a few seed rows so a fresh designer has a starting point
    assert "first_blood" in body
    assert "collector_10" in body or "completionist" in body
    print("OK starter_files() includes achievements.md with sections + 3 trigger kinds + seed rows")


# ───────────────────────────────────────────── doc r/w round-trip


def test_read_achievements_returns_empty_when_absent() -> None:
    _fresh_studio()
    result = studio_read_achievements()
    assert result["ok"] is True
    assert result["content"] == ""
    print("OK read_achievements: empty when file absent")


def test_write_then_read_achievements_round_trip() -> None:
    state, _ = _fresh_studio()
    body = (
        "# Achievements\n\n## Roster\n"
        "| Key | Trigger | Threshold | Unlock Message |\n"
        "|-----|---------|-----------|----------------|\n"
        "| first_blood | ScoreAtLeast | 1 | First score! |\n"
        "| complete | ScoreAtLeast | 30 | All coins! |\n"
    )
    write_result = studio_write_achievements(content=body)
    assert write_result["ok"] is True
    assert write_result["path"] == str(state.paths.achievements)
    read_result = studio_read_achievements()
    assert "first_blood" in read_result["content"]
    assert "ScoreAtLeast" in read_result["content"]
    print("OK achievements write then read round-trips")


# ───────────────────────────────────────────── role allowlist


def test_achievement_designer_allowlist() -> None:
    assert "studio_read_achievements" in ACHIEVEMENT_DESIGNER.tool_set
    assert "studio_write_achievements" in ACHIEVEMENT_DESIGNER.tool_set
    # Reads adjacent context
    assert "studio_read_gdd" in ACHIEVEMENT_DESIGNER.tool_set
    assert "studio_read_scene_catalog" in ACHIEVEMENT_DESIGNER.tool_set
    # Lifecycle + escalation
    assert "studio_update_task_status" in ACHIEVEMENT_DESIGNER.tool_set
    assert "studio_add_task" in ACHIEVEMENT_DESIGNER.tool_set
    assert "studio_propose_decision" in ACHIEVEMENT_DESIGNER.tool_set
    # Cannot write any OTHER doc
    for tool in ("studio_write_gdd", "studio_write_art_bible",
                  "studio_write_audio_brief", "studio_write_press_kit",
                  "studio_write_tutorial", "studio_write_scene_catalog",
                  "studio_write_strings"):
        assert tool not in ACHIEVEMENT_DESIGNER.tool_set, (
            f"Achievement Designer must not have {tool}"
        )
    # Cannot mutate scene
    assert "unity_create_primitive" not in ACHIEVEMENT_DESIGNER.tool_set
    assert "unity_attach_behaviour" not in ACHIEVEMENT_DESIGNER.tool_set
    print("OK Achievement Designer allowlist: roster r/w + GDD + scene catalog reads + tasks/decisions, NOTHING ELSE")


def test_other_roles_lack_achievements_write() -> None:
    """Only Achievement Designer writes the roster."""
    for role in (ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR,
                  BUILD_ENGINEER, CAMERA_DIRECTOR, DESIGNER,
                  GAME_BALANCER, LIGHTING_DIRECTOR, LOCALIZATION_LEAD,
                  MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
                  SCENE_DIRECTOR, TUTORIAL_DESIGNER, UI_BUILDER,
                  VFX_DIRECTOR, WORKER):
        assert "studio_write_achievements" not in role.tool_set, (
            f"{role.id} must not write the achievements roster"
        )
    print("OK only Achievement Designer writes the achievements roster")


def test_worker_reads_achievements_roster() -> None:
    """The Worker attaches one Achievement component per row in the
    roster — it needs READ access to know what to attach. Cannot
    write."""
    assert "studio_read_achievements" in WORKER.tool_set
    assert "studio_write_achievements" not in WORKER.tool_set
    print("OK Worker reads (but does not write) the achievements roster")


def test_achievement_designer_doc_only_no_engine() -> None:
    assert ACHIEVEMENT_DESIGNER.needs_engine is False
    assert ACHIEVEMENT_DESIGNER.needs_vision is False
    print("OK Achievement Designer is engine-free + vision-free (doc-only)")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_achievement_designer_to_self() -> None:
    assert DISPATCH_MAP["achievement_designer"] == "achievement_designer"
    print("OK DISPATCH_MAP[achievement_designer] -> achievement_designer")


def test_achievement_designer_in_roles_validation_tuple() -> None:
    from unitytools.studio.models import ROLES
    assert "achievement_designer" in ROLES, (
        "achievement_designer must be in ROLES so studio_add_task accepts it"
    )
    print("OK achievement_designer is in ROLES validation tuple")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["tutorial_designer"] == "tutorial_designer"
    assert DISPATCH_MAP["scene_director"] == "scene_director"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after achievement_designer addition")


def run_test() -> None:
    # Path + template
    test_paths_expose_achievements()
    test_starter_files_include_achievements_template()
    # Doc r/w
    test_read_achievements_returns_empty_when_absent()
    test_write_then_read_achievements_round_trip()
    # Role
    test_achievement_designer_allowlist()
    test_other_roles_lack_achievements_write()
    test_worker_reads_achievements_roster()
    test_achievement_designer_doc_only_no_engine()
    # Dispatch
    test_dispatch_map_routes_achievement_designer_to_self()
    test_achievement_designer_in_roles_validation_tuple()
    test_existing_routes_unchanged()
    print("All Phase 51 achievement designer tests passed")


if __name__ == "__main__":
    run_test()
