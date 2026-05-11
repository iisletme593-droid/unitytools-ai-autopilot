"""Phase 46 tests: studio_scaffold_endless_runner_game.

Third game-genre scaffolder. Uses the new endless-runner primitives
(AutoScroller + LanePositioner) plus the existing combat (Enemy as
collidable obstacle) and game-loop (GameSession, Collectible)
libraries. Verifies validation, milestone + task creation, specialist
role coverage including Worker recipe embedding the
LanePositioner / AutoScroller wiring with the passed-in params.
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
from unitytools.studio.tools import studio_scaffold_endless_runner_game


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="runner-scaffold-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── validation


def test_runner_rejects_single_lane() -> None:
    """An endless runner with 1 lane is just an auto-scroller; the
    LanePositioner needs at least 2 lanes to be meaningful."""
    _fresh_studio()
    result = studio_scaffold_endless_runner_game(lane_count=1)
    assert result["ok"] is False
    assert "lane_count" in result["error"]
    print("OK lane_count=1 rejected (need at least 2 lanes)")


def test_runner_rejects_too_many_lanes() -> None:
    _fresh_studio()
    result = studio_scaffold_endless_runner_game(lane_count=20)
    assert result["ok"] is False
    print("OK lane_count > 7 rejected")


def test_runner_rejects_zero_speed() -> None:
    _fresh_studio()
    result = studio_scaffold_endless_runner_game(scroll_speed=0.0)
    assert result["ok"] is False
    assert "scroll_speed" in result["error"]
    print("OK scroll_speed=0 rejected (no scroll = no runner)")


def test_runner_rejects_zero_obstacle_interval() -> None:
    _fresh_studio()
    result = studio_scaffold_endless_runner_game(obstacle_interval=0.0)
    assert result["ok"] is False
    print("OK obstacle_interval=0 rejected")


def test_runner_rejects_huge_target_score() -> None:
    _fresh_studio()
    result = studio_scaffold_endless_runner_game(target_score=10_000)
    assert result["ok"] is False
    print("OK target_score > 500 rejected")


# ───────────────────────────────────────────── happy path


def test_runner_scaffold_creates_milestone_and_tasks() -> None:
    state, _ = _fresh_studio()
    result = studio_scaffold_endless_runner_game(
        game_name="Lane Sprinter",
        lane_count=3,
        scroll_speed=10.0,
        obstacle_interval=1.2,
        target_score=20,
    )
    assert result["ok"] is True
    assert result["lane_count"] == 3
    milestones = state.load_milestones()
    assert len(milestones) == 1
    assert "Lane Sprinter" in milestones[0].name

    tasks = state.load_tasks()
    assert len(tasks) == result["task_count"]
    # Endless runner scaffold should match shooter's 15 tasks (same
    # specialist coverage)
    assert len(tasks) >= 14
    for t in tasks:
        assert t.milestone == result["milestone_id"]
    print(f"OK runner scaffold opens {len(tasks)} tasks all linked to one milestone")


def test_runner_scaffold_covers_specialist_pipeline() -> None:
    _fresh_studio()
    result = studio_scaffold_endless_runner_game()
    roles = {t["role"] for t in result["tasks"]}
    must_have = {
        "designer", "art_director", "worker", "ui_builder",
        "lighting_director", "atmosphere_director", "camera_director",
        "material_artist", "audio_director", "localization_lead",
        "marketing_director", "physics_qa",
        "playtester", "game_balancer", "build_engineer",
    }
    missing = must_have - roles
    assert not missing, f"runner scaffold missing tasks for roles: {missing}"
    print(f"OK runner scaffold covers all {len(must_have)} required specialists")


def test_runner_worker_task_embeds_lane_and_scroller_wiring() -> None:
    """The Worker recipe must reference LanePositioner + AutoScroller +
    the two template GOs (CoinTemplate + ObstacleTemplate) that the
    Spawners clone."""
    state, _ = _fresh_studio()
    studio_scaffold_endless_runner_game(lane_count=4, lane_width=2.5)
    worker = next(t for t in state.load_tasks() if t.role == "worker")
    body = worker.description
    for primitive in ("LanePositioner", "AutoScroller", "Spawner",
                       "Collectible", "Enemy", "GameSession", "Rotator"):
        assert primitive in body, f"worker task missing {primitive}"
    assert "CoinTemplate" in body
    assert "ObstacleTemplate" in body
    assert "CoinSpawner" in body
    assert "ObstacleSpawner" in body
    # Lane params flow through
    assert "'laneCount': 4" in body
    assert "'laneWidth': 2.5" in body
    print("OK Worker task wires LanePositioner + AutoScroller + 2 templates + 2 spawners with passed params")


def test_runner_worker_task_passes_through_scroll_params() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_endless_runner_game(
        scroll_speed=12.0, obstacle_interval=2.0, target_score=42,
    )
    worker = next(t for t in state.load_tasks() if t.role == "worker")
    body = worker.description
    assert "'speed': 12.0" in body
    assert "'interval': 2.0" in body  # obstacle spawner interval
    assert "winScore': 42" in body
    print("OK runner Worker recipe substitutes scroll_speed + obstacle_interval + target_score")


def test_runner_camera_director_uses_follow_target() -> None:
    """Endless-runner camera must follow the lane-switching player so
    the lateral motion is visible."""
    state, _ = _fresh_studio()
    studio_scaffold_endless_runner_game()
    cam = next(t for t in state.load_tasks() if t.role == "camera_director")
    assert "FollowTarget" in cam.description
    assert "'targetName': 'Player'" in cam.description
    assert "Main Camera" in cam.description
    print("OK Camera Director task attaches FollowTarget on Main Camera")


def test_runner_material_artist_uses_emission_on_obstacle() -> None:
    """Obstacles in a runner need to read as DANGER through fog — HDR
    emission with a warning tint."""
    state, _ = _fresh_studio()
    studio_scaffold_endless_runner_game()
    mat = next(t for t in state.load_tasks() if t.role == "material_artist")
    assert "ObstacleTemplate" in mat.description
    assert "emission_enabled=1" in mat.description
    print("OK Material Artist task enables emission on ObstacleTemplate (visibility through fog)")


def test_runner_build_engineer_ships_windows_and_webgl() -> None:
    """Endless runners are perfect WebGL distribution material — the
    build engineer task should target both windows + webgl."""
    state, _ = _fresh_studio()
    studio_scaffold_endless_runner_game()
    build = next(t for t in state.load_tasks() if t.role == "build_engineer")
    assert "target='windows'" in build.description
    assert "target='webgl'" in build.description
    assert "index.html" in build.description
    print("OK Build Engineer task ships BOTH windows + webgl (runners love WebGL)")


def test_runner_localization_includes_runner_specific_keys() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_endless_runner_game()
    loc = next(t for t in state.load_tasks() if t.role == "localization_lead")
    # Runner has 'btn.start' label as "Run" not "Start" — runner-specific feel
    assert "Run" in loc.description
    # screen.win + screen.lose for win + crash paths
    assert "screen.win" in loc.description
    assert "screen.lose" in loc.description
    print("OK Localization task includes runner-specific keys")


# ───────────────────────────────────────────── Producer access


def test_producer_can_call_runner_scaffolder() -> None:
    assert "studio_scaffold_endless_runner_game" in PRODUCER.tool_set
    print("OK Producer allowlist exposes studio_scaffold_endless_runner_game")


def test_runner_scaffolder_not_available_to_specialists() -> None:
    from unitytools.studio import (
        ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR, BUILD_ENGINEER,
        CAMERA_DIRECTOR, CRITIC, DESIGNER, GAME_BALANCER, LIGHTING_DIRECTOR,
        LOCALIZATION_LEAD, MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
        UI_BUILDER, VFX_DIRECTOR, WORKER,
    )
    for role in (ART_DIRECTOR, ATMOSPHERE_DIRECTOR, AUDIO_DIRECTOR,
                  BUILD_ENGINEER, CAMERA_DIRECTOR, CRITIC, DESIGNER,
                  GAME_BALANCER, LIGHTING_DIRECTOR, LOCALIZATION_LEAD,
                  MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
                  UI_BUILDER, VFX_DIRECTOR, WORKER):
        assert "studio_scaffold_endless_runner_game" not in role.tool_set, (
            f"{role.id} must not call the runner scaffolder"
        )
    print("OK only Producer can scaffold an endless runner; specialists cannot")


def run_test() -> None:
    # Validation
    test_runner_rejects_single_lane()
    test_runner_rejects_too_many_lanes()
    test_runner_rejects_zero_speed()
    test_runner_rejects_zero_obstacle_interval()
    test_runner_rejects_huge_target_score()
    # Happy path
    test_runner_scaffold_creates_milestone_and_tasks()
    test_runner_scaffold_covers_specialist_pipeline()
    test_runner_worker_task_embeds_lane_and_scroller_wiring()
    test_runner_worker_task_passes_through_scroll_params()
    test_runner_camera_director_uses_follow_target()
    test_runner_material_artist_uses_emission_on_obstacle()
    test_runner_build_engineer_ships_windows_and_webgl()
    test_runner_localization_includes_runner_specific_keys()
    # Producer surface
    test_producer_can_call_runner_scaffolder()
    test_runner_scaffolder_not_available_to_specialists()
    print("All Phase 46 endless-runner scaffold tests passed")


if __name__ == "__main__":
    run_test()
