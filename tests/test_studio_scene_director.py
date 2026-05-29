"""Phase 48 tests: Scene Director role + scene_catalog.md doc.

Doc-only pattern. Verifies path + template, read/write round-trip,
role allowlist isolation (Scene Director reads but doesn't write
other docs; Worker + Build Engineer can READ the catalog but only
Scene Director writes), dispatch routing.
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
    studio_read_scene_catalog,
    studio_write_scene_catalog,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="scene-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── path + template


def test_paths_expose_scene_catalog() -> None:
    state, _ = _fresh_studio()
    assert state.paths.scene_catalog.name == "scene_catalog.md"
    assert state.paths.scene_catalog.parent == state.paths.root
    print("OK StudioPaths.scene_catalog -> studio/scene_catalog.md")


def test_starter_files_include_scene_catalog_template() -> None:
    files = starter_files()
    assert "scene_catalog.md" in files
    body = files["scene_catalog.md"]
    # Canonical sections the role's prompt depends on
    for section in ("Scenes", "Transitions", "Build Settings",
                     "Persistent State"):
        assert section in body, f"scene_catalog.md missing section: {section}"
    # Baseline 4-scene MVP listed: Title / Game / Win / GameOver
    for scene_name in ("Title.unity", "Game.unity", "Win.unity", "GameOver.unity"):
        assert scene_name in body, f"template missing {scene_name}"
    # Transitions list contains the expected MVP transitions
    assert "Title  -> Game" in body or "Title -> Game" in body
    print("OK starter_files() includes scene_catalog.md with canonical sections + 4-scene MVP baseline")


# ───────────────────────────────────────────── doc r/w round-trip


def test_read_scene_catalog_returns_empty_when_absent() -> None:
    _fresh_studio()
    result = studio_read_scene_catalog()
    assert result["ok"] is True
    assert result["content"] == ""
    print("OK read_scene_catalog: empty when file absent")


def test_write_then_read_scene_catalog_round_trip() -> None:
    state, _ = _fresh_studio()
    body = (
        "# Scene Catalog\n\n## Scenes\n"
        "| Path | Role | Loaded by | Notes |\n"
        "|------|------|-----------|-------|\n"
        "| Assets/Scenes/Title.unity | title | scene 0 | start button |\n"
        "## Transitions\n- Title -> Game via Start button\n"
    )
    write_result = studio_write_scene_catalog(content=body)
    assert write_result["ok"] is True
    assert write_result["path"] == str(state.paths.scene_catalog)
    assert state.paths.scene_catalog.exists()

    read_result = studio_read_scene_catalog()
    assert "Title.unity" in read_result["content"]
    assert "Start button" in read_result["content"]
    print("OK scene catalog write then read round-trips")


# ───────────────────────────────────────────── role allowlist


def test_scene_director_allowlist() -> None:
    """Scene Director reads GDD + tutorial + press kit for context,
    writes ONLY the scene catalog, files follow-up tasks. Cannot
    touch any other doc or mutate scenes."""
    assert "studio_read_scene_catalog" in SCENE_DIRECTOR.tool_set
    assert "studio_write_scene_catalog" in SCENE_DIRECTOR.tool_set
    # Reads adjacent context docs
    assert "studio_read_gdd" in SCENE_DIRECTOR.tool_set
    assert "studio_read_tutorial" in SCENE_DIRECTOR.tool_set
    assert "studio_read_press_kit" in SCENE_DIRECTOR.tool_set
    # Lifecycle + escalation
    assert "studio_add_task" in SCENE_DIRECTOR.tool_set
    assert "studio_propose_decision" in SCENE_DIRECTOR.tool_set
    assert "studio_update_task_status" in SCENE_DIRECTOR.tool_set
    # Cannot write any OTHER doc
    assert "studio_write_gdd" not in SCENE_DIRECTOR.tool_set
    assert "studio_write_art_bible" not in SCENE_DIRECTOR.tool_set
    assert "studio_write_audio_brief" not in SCENE_DIRECTOR.tool_set
    assert "studio_write_press_kit" not in SCENE_DIRECTOR.tool_set
    assert "studio_write_tutorial" not in SCENE_DIRECTOR.tool_set
    assert "studio_write_strings" not in SCENE_DIRECTOR.tool_set
    # Cannot mutate scene / build / play mode
    assert "unity_create_primitive" not in SCENE_DIRECTOR.tool_set
    assert "unity_add_scene_to_build" not in SCENE_DIRECTOR.tool_set
    assert "unity_build_player" not in SCENE_DIRECTOR.tool_set
    assert "studio_playtest_smoke" not in SCENE_DIRECTOR.tool_set
    print("OK Scene Director allowlist: catalog r/w + adjacent reads + tasks/decisions, no other doc writes, no scene/build mutation")


def test_other_roles_lack_scene_catalog_write() -> None:
    for role in (ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR,
                  BUILD_ENGINEER, CAMERA_DIRECTOR, DESIGNER,
                  GAME_BALANCER, LIGHTING_DIRECTOR, LOCALIZATION_LEAD,
                  MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
                  TUTORIAL_DESIGNER, UI_BUILDER, VFX_DIRECTOR, WORKER):
        assert "studio_write_scene_catalog" not in role.tool_set, (
            f"{role.id} must not write the scene catalog"
        )
    print("OK only Scene Director writes the scene catalog")


def test_worker_can_read_scene_catalog() -> None:
    """The Worker wires LoadSceneOnClick.sceneName + GameSession's
    win/lose scene names. It needs to READ the catalog (but not
    write it) so those names align with Scene Director's plan."""
    assert "studio_read_scene_catalog" in WORKER.tool_set
    assert "studio_write_scene_catalog" not in WORKER.tool_set
    print("OK Worker reads (but does not write) the scene catalog")


def test_build_engineer_can_read_catalog_and_add_to_build_settings() -> None:
    """The Build Engineer reads the catalog's build-settings checklist
    and uses unity_add_scene_to_build to populate EditorBuildSettings.
    Both abilities required."""
    assert "studio_read_scene_catalog" in BUILD_ENGINEER.tool_set
    assert "studio_write_scene_catalog" not in BUILD_ENGINEER.tool_set
    assert "unity_add_scene_to_build" in BUILD_ENGINEER.tool_set
    print("OK Build Engineer reads catalog + can add scenes to EditorBuildSettings")


def test_scene_director_doc_only_no_engine() -> None:
    assert SCENE_DIRECTOR.needs_engine is False
    assert SCENE_DIRECTOR.needs_vision is False
    print("OK Scene Director is engine-free + vision-free (doc-only)")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_scene_director_to_self() -> None:
    assert DISPATCH_MAP["scene_director"] == "scene_director"
    print("OK DISPATCH_MAP[scene_director] -> scene_director")


def test_scene_director_in_roles_validation_tuple() -> None:
    from unitytools.studio.models import ROLES
    assert "scene_director" in ROLES, (
        "scene_director must be in ROLES so studio_add_task accepts it"
    )
    print("OK scene_director is in ROLES validation tuple")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["tutorial_designer"] == "tutorial_designer"
    assert DISPATCH_MAP["localization_lead"] == "localization_lead"
    assert DISPATCH_MAP["marketing_director"] == "marketing_director"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after scene_director addition")


def run_test() -> None:
    # Path + template
    test_paths_expose_scene_catalog()
    test_starter_files_include_scene_catalog_template()
    # Doc r/w
    test_read_scene_catalog_returns_empty_when_absent()
    test_write_then_read_scene_catalog_round_trip()
    # Role
    test_scene_director_allowlist()
    test_other_roles_lack_scene_catalog_write()
    test_worker_can_read_scene_catalog()
    test_build_engineer_can_read_catalog_and_add_to_build_settings()
    test_scene_director_doc_only_no_engine()
    # Dispatch
    test_dispatch_map_routes_scene_director_to_self()
    test_scene_director_in_roles_validation_tuple()
    test_existing_routes_unchanged()
    print("All Phase 48 scene director tests passed")


if __name__ == "__main__":
    run_test()
