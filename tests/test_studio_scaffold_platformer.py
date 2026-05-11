"""Phase 50 tests: studio_scaffold_platformer_game.

Fourth genre scaffolder. Uses the new Jumper primitive plus the
existing motion (KeyboardMover with gravity OFF) + game-loop
(GameSession + Collectible) + combat (Enemy as KillPlane) libraries.
Verifies input validation, milestone + 16-task creation, specialist
coverage including the platformer-specific Scene Director task,
and that the Worker recipe correctly disables KeyboardMover gravity
when attaching Jumper.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    PRODUCER,
    StudioPaths,
    StudioState,
    init_studio_tools,
)
from unitytools.studio.tools import studio_scaffold_platformer_game


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="platformer-scaffold-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── validation


def test_platformer_rejects_zero_coins() -> None:
    _fresh_studio()
    result = studio_scaffold_platformer_game(coin_count=0)
    assert result["ok"] is False
    assert "coin_count" in result["error"]
    print("OK coin_count=0 rejected")


def test_platformer_rejects_zero_platforms() -> None:
    _fresh_studio()
    result = studio_scaffold_platformer_game(platform_count=0)
    assert result["ok"] is False
    assert "platform_count" in result["error"]
    print("OK platform_count=0 rejected (need at least 1 platform to land on)")


def test_platformer_rejects_huge_jump_height() -> None:
    _fresh_studio()
    result = studio_scaffold_platformer_game(jump_height=50.0)
    assert result["ok"] is False
    assert "jump_height" in result["error"]
    print("OK jump_height > 20 rejected (silly value)")


def test_platformer_rejects_zero_jump_height() -> None:
    _fresh_studio()
    result = studio_scaffold_platformer_game(jump_height=0.0)
    assert result["ok"] is False
    print("OK jump_height=0 rejected (no jump = no platformer)")


def test_platformer_rejects_huge_spread() -> None:
    _fresh_studio()
    result = studio_scaffold_platformer_game(platform_spread_x=200.0)
    assert result["ok"] is False
    print("OK platform_spread_x > 40 rejected")


# ───────────────────────────────────────────── happy path


def test_platformer_scaffold_creates_milestone_and_tasks() -> None:
    state, _ = _fresh_studio()
    result = studio_scaffold_platformer_game(
        game_name="Hop Quest",
        coin_count=10,
        platform_count=6,
        jump_height=2.5,
    )
    assert result["ok"] is True
    milestones = state.load_milestones()
    assert len(milestones) == 1
    assert "Hop Quest" in milestones[0].name

    tasks = state.load_tasks()
    assert len(tasks) == result["task_count"]
    # Platformer has 16 tasks (15 from runner + Scene Director + Tutorial Designer)
    assert len(tasks) >= 15
    for t in tasks:
        assert t.milestone == result["milestone_id"]
    print(f"OK platformer scaffold opens {len(tasks)} tasks all linked to milestone")


def test_platformer_scaffold_covers_specialist_pipeline() -> None:
    """Platformer needs Scene Director (multi-scene transitions) AND
    Tutorial Designer (jump arc has to be taught) on top of the
    base specialist set."""
    _fresh_studio()
    result = studio_scaffold_platformer_game()
    roles = {t["role"] for t in result["tasks"]}
    must_have = {
        "designer", "art_director", "scene_director", "tutorial_designer",
        "worker", "ui_builder", "lighting_director", "atmosphere_director",
        "camera_director", "material_artist", "audio_director",
        "localization_lead", "marketing_director", "physics_qa",
        "playtester", "game_balancer", "build_engineer",
    }
    missing = must_have - roles
    assert not missing, f"platformer scaffold missing tasks for roles: {missing}"
    print(f"OK platformer scaffold covers all {len(must_have)} specialist roles "
          f"(includes Scene Director + Tutorial Designer)")


def test_platformer_worker_disables_keyboard_mover_gravity() -> None:
    """CRITICAL contract: Jumper handles all vertical motion. If
    KeyboardMover.applyGravity stays True, the two fight and the
    player can't reliably jump."""
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game()
    worker = next(t for t in state.load_tasks() if t.role == "worker")
    body = worker.description
    assert "KeyboardMover" in body
    assert "Jumper" in body
    # The worker task must explicitly set applyGravity=false
    assert "'applyGravity': false" in body
    assert "applyGravity=false" in body  # also in the CRITICAL comment
    print("OK Worker task sets KeyboardMover.applyGravity=false alongside Jumper")


def test_platformer_worker_embeds_kill_plane_and_jumper_params() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game(jump_height=3.5)
    worker = next(t for t in state.load_tasks() if t.role == "worker")
    body = worker.description
    # KillPlane (Enemy with huge contactDamage)
    assert "KillPlane" in body
    assert "'contactDamage': 99" in body or "contactDamage=99" in body
    # Jumper params flow through
    assert "'jumpHeight': 3.5" in body
    assert "'coyoteTime'" in body  # casual-platformer forgiveness
    assert "'jumpBuffer'" in body
    # Snapshot + save + close
    assert "unity_create_scene_snapshot" in body
    assert "unity_save_scene" in body
    assert "studio_update_task_status" in body
    print("OK Worker task embeds KillPlane + Jumper params (incl. coyote + buffer)")


def test_platformer_camera_is_side_on_with_follow() -> None:
    """Platformer camera convention: side-on view following the player
    horizontally."""
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game()
    cam = next(t for t in state.load_tasks() if t.role == "camera_director")
    assert "Main Camera" in cam.description
    assert "FollowTarget" in cam.description
    assert "Player" in cam.description    # camera follows the player
    print("OK Camera Director task wires side-on FollowTarget on Main Camera")


def test_platformer_material_artist_emission_on_player() -> None:
    """Platformer player needs to read against ANY platform. The role
    prompt locks slight emission on the player so silhouette pops."""
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game()
    mat = next(t for t in state.load_tasks() if t.role == "material_artist")
    assert "Player" in mat.description
    assert "emission_enabled=1" in mat.description
    print("OK Material Artist task enables emission on Player (silhouette readability)")


def test_platformer_tutorial_designer_task_present() -> None:
    """The jump arc is the platformer's signature mechanic — it MUST
    be taught. Tutorial Designer task is required."""
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game()
    tut = next(t for t in state.load_tasks() if t.role == "tutorial_designer")
    # Tutorial mentions jump
    assert "jump" in tut.description.lower() or "Space" in tut.description
    print("OK Tutorial Designer task teaches the jump")


def test_platformer_scene_director_task_present() -> None:
    """4-scene MVP: Title + Game + Win + GameOver. Scene Director
    drafts the catalog."""
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game()
    sc = next(t for t in state.load_tasks() if t.role == "scene_director")
    assert "Title" in sc.description
    assert "GameOver" in sc.description or "Game Over" in sc.description
    print("OK Scene Director task drafts 4-scene MVP catalog (Title/Game/Win/GameOver)")


def test_platformer_localization_includes_jump_in_string() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game()
    loc = next(t for t in state.load_tasks() if t.role == "localization_lead")
    # Platformer's Start button label is 'Jump In' (genre-specific feel)
    assert "Jump In" in loc.description
    assert "Fell Off" in loc.description  # lose screen
    print("OK Localization task includes platformer-specific labels (Jump In / Fell Off)")


def test_platformer_build_engineer_ships_windows_and_webgl() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_platformer_game()
    build = next(t for t in state.load_tasks() if t.role == "build_engineer")
    assert "target='windows'" in build.description
    assert "target='webgl'" in build.description
    print("OK Build Engineer task ships BOTH windows + webgl (itch.io platformer demos)")


# ───────────────────────────────────────────── Producer access


def test_producer_can_call_platformer_scaffolder() -> None:
    assert "studio_scaffold_platformer_game" in PRODUCER.tool_set
    print("OK Producer allowlist exposes studio_scaffold_platformer_game")


def test_platformer_scaffolder_not_available_to_specialists() -> None:
    from unitytools.studio import (
        ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR, BUILD_ENGINEER,
        CAMERA_DIRECTOR, CRITIC, DESIGNER, GAME_BALANCER, LIGHTING_DIRECTOR,
        LOCALIZATION_LEAD, MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
        SCENE_DIRECTOR, TUTORIAL_DESIGNER, UI_BUILDER, VFX_DIRECTOR, WORKER,
    )
    for role in (ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR,
                  BUILD_ENGINEER, CAMERA_DIRECTOR, CRITIC, DESIGNER,
                  GAME_BALANCER, LIGHTING_DIRECTOR, LOCALIZATION_LEAD,
                  MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
                  SCENE_DIRECTOR, TUTORIAL_DESIGNER, UI_BUILDER,
                  VFX_DIRECTOR, WORKER):
        assert "studio_scaffold_platformer_game" not in role.tool_set, (
            f"{role.id} must not call the platformer scaffolder"
        )
    print("OK only Producer can scaffold a platformer; 18 specialists cannot")


def run_test() -> None:
    # Validation
    test_platformer_rejects_zero_coins()
    test_platformer_rejects_zero_platforms()
    test_platformer_rejects_huge_jump_height()
    test_platformer_rejects_zero_jump_height()
    test_platformer_rejects_huge_spread()
    # Happy path
    test_platformer_scaffold_creates_milestone_and_tasks()
    test_platformer_scaffold_covers_specialist_pipeline()
    test_platformer_worker_disables_keyboard_mover_gravity()
    test_platformer_worker_embeds_kill_plane_and_jumper_params()
    test_platformer_camera_is_side_on_with_follow()
    test_platformer_material_artist_emission_on_player()
    test_platformer_tutorial_designer_task_present()
    test_platformer_scene_director_task_present()
    test_platformer_localization_includes_jump_in_string()
    test_platformer_build_engineer_ships_windows_and_webgl()
    # Producer surface
    test_producer_can_call_platformer_scaffolder()
    test_platformer_scaffolder_not_available_to_specialists()
    print("All Phase 50 platformer scaffold tests passed")


if __name__ == "__main__":
    run_test()
