"""Phase 44 tests: studio_scaffold_top_down_shooter_game.

The action-genre scaffolder uses the Phase 43 combat primitives
(Projectile / Shooter / Spawner / Enemy) plus the existing Behaviour
Library. Verify input validation, milestone + task creation, role
coverage (including game_balancer + physics_qa which were optional
for collectathon), and that the Worker task embeds the combat
template recipe accurately.
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
from unitytools.studio.tools import studio_scaffold_top_down_shooter_game


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="shooter-scaffold-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── validation


def test_shooter_scaffold_rejects_zero_kills() -> None:
    _fresh_studio()
    result = studio_scaffold_top_down_shooter_game(target_kills=0)
    assert result["ok"] is False
    assert "target_kills" in result["error"]
    print("OK target_kills=0 rejected")


def test_shooter_scaffold_rejects_too_many_kills() -> None:
    _fresh_studio()
    result = studio_scaffold_top_down_shooter_game(target_kills=1000)
    assert result["ok"] is False
    assert "target_kills" in result["error"]
    print("OK target_kills > 500 rejected")


def test_shooter_scaffold_rejects_zero_interval() -> None:
    _fresh_studio()
    result = studio_scaffold_top_down_shooter_game(spawn_interval=0.0)
    assert result["ok"] is False
    assert "spawn_interval" in result["error"]
    print("OK spawn_interval=0 rejected")


def test_shooter_scaffold_rejects_huge_max_alive() -> None:
    _fresh_studio()
    result = studio_scaffold_top_down_shooter_game(max_alive=100)
    assert result["ok"] is False
    assert "max_alive" in result["error"]
    print("OK max_alive > 50 rejected")


def test_shooter_scaffold_rejects_negative_play_area() -> None:
    _fresh_studio()
    result = studio_scaffold_top_down_shooter_game(play_area_radius=-1.0)
    assert result["ok"] is False
    assert "play_area_radius" in result["error"]
    print("OK negative play_area_radius rejected")


# ───────────────────────────────────────────── happy path


def test_shooter_scaffold_creates_milestone_and_tasks() -> None:
    state, _ = _fresh_studio()
    result = studio_scaffold_top_down_shooter_game(
        game_name="Wave Hunter",
        target_kills=25,
        spawn_interval=1.5,
        max_alive=4,
        play_area_radius=10.0,
    )
    assert result["ok"] is True
    assert result["target_kills"] == 25
    milestones = state.load_milestones()
    assert len(milestones) == 1
    assert milestones[0].id == result["milestone_id"]
    assert "Wave Hunter" in milestones[0].name

    tasks = state.load_tasks()
    assert len(tasks) == result["task_count"]
    assert len(tasks) >= 12
    for t in tasks:
        assert t.milestone == result["milestone_id"]
    print(f"OK shooter scaffold opens {len(tasks)} tasks all linked to one milestone")


def test_shooter_scaffold_covers_action_specialist_roles() -> None:
    """Action genre needs more specialists than collectathon: game_balancer
    + physics_qa become required (wave spawning blows perf if unchecked,
    and combat needs balance feedback)."""
    _fresh_studio()
    result = studio_scaffold_top_down_shooter_game()
    roles = {t["role"] for t in result["tasks"]}

    must_have = {
        "designer", "art_director", "worker", "ui_builder",
        "lighting_director", "atmosphere_director", "camera_director",
        "material_artist", "audio_director", "localization_lead",
        "marketing_director", "physics_qa",    # action: wave perf check
        "playtester", "game_balancer",         # action: tune via playtest data
        "build_engineer",
    }
    missing = must_have - roles
    assert not missing, f"shooter scaffold missing tasks for roles: {missing}"
    print(f"OK shooter scaffold covers all {len(must_have)} required specialists "
          f"(includes physics_qa + game_balancer for action-genre tuning)")


def test_shooter_worker_task_embeds_combat_template_recipe() -> None:
    """The Worker task must name every combat primitive plus the
    template GameObjects they reference."""
    state, _ = _fresh_studio()
    studio_scaffold_top_down_shooter_game()
    worker = next(t for t in state.load_tasks() if t.role == "worker")
    body = worker.description
    # Combat primitives by name
    for primitive in ("Projectile", "Shooter", "Spawner", "Enemy", "KeyboardMover",
                       "FollowTarget", "GameSession"):
        assert primitive in body, f"worker task missing {primitive}"
    # Template names (Shooter resolves by string)
    assert "ProjectileTemplate" in body
    assert "EnemyTemplate" in body
    # Trigger collider setup
    assert "isTrigger" in body
    # Snapshot at start
    assert "unity_create_scene_snapshot" in body
    # Save + close
    assert "unity_save_scene" in body
    assert "studio_update_task_status" in body
    print("OK Worker task embeds ProjectileTemplate / EnemyTemplate + 7 behaviour names + snapshot/save/close")


def test_shooter_worker_task_passes_through_scaffold_params() -> None:
    """winScore, spawn interval, max_alive, play_area_radius should
    all be substituted into the Worker description rather than hard-
    coded literals."""
    state, _ = _fresh_studio()
    studio_scaffold_top_down_shooter_game(
        target_kills=42,
        spawn_interval=3.5,
        max_alive=8,
        play_area_radius=14.0,
    )
    worker = next(t for t in state.load_tasks() if t.role == "worker")
    body = worker.description
    assert "winScore': 42" in body
    assert "'interval': 3.5" in body
    assert "'maxAlive': 8" in body
    assert "'spawnRadius': 14.0" in body
    print("OK scaffold params (winScore/interval/maxAlive/spawnRadius) substituted into Worker recipe")


def test_shooter_ui_builder_task_uses_lives_token() -> None:
    """Top-down shooter HUD shows kills + lives; the format string
    must reference {lives} (collectathon only used {score}/{win})."""
    state, _ = _fresh_studio()
    studio_scaffold_top_down_shooter_game()
    ui = next(t for t in state.load_tasks() if t.role == "ui_builder")
    assert "{score}" in ui.description
    assert "{win}" in ui.description
    assert "{lives}" in ui.description, "shooter HUD must show lives — combat genre has a fail state"
    print("OK UI Builder task includes Lives in HUD format (action genre needs fail state visible)")


def test_shooter_material_artist_uses_emission_for_projectile() -> None:
    """Projectiles must read as HDR energy bolts so the player tracks
    them mid-flight against the background."""
    state, _ = _fresh_studio()
    studio_scaffold_top_down_shooter_game()
    mat = next(t for t in state.load_tasks() if t.role == "material_artist")
    assert "ProjectileTemplate" in mat.description
    assert "emission_enabled=1" in mat.description
    print("OK Material Artist task enables emission on ProjectileTemplate")


def test_shooter_localization_includes_lose_screen() -> None:
    """Combat genre adds a lose path — string table must include
    screen.lose alongside screen.win."""
    state, _ = _fresh_studio()
    studio_scaffold_top_down_shooter_game()
    loc = next(t for t in state.load_tasks() if t.role == "localization_lead")
    assert "screen.win" in loc.description
    assert "screen.lose" in loc.description
    print("OK Localization task includes screen.lose key (combat has a fail state)")


def test_shooter_game_balancer_task_references_balance_audit() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_top_down_shooter_game()
    bal = next(t for t in state.load_tasks() if t.role == "game_balancer")
    assert "studio_balance_audit" in bal.description
    assert "playtest_failure_rate" in bal.description
    print("OK Game Balancer task references the balance_audit tool + failure-rate threshold")


def test_shooter_marketing_normalises_bundle_id() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_top_down_shooter_game(game_name="Neon Wave Hunter")
    mkt = next(t for t in state.load_tasks() if t.role == "marketing_director")
    assert "com.unitytools.neonwavehunter" in mkt.description
    print("OK marketing task carries lowercased bundle_id from multi-word game_name")


# ───────────────────────────────────────────── Producer access


def test_producer_can_call_shooter_scaffolder() -> None:
    assert "studio_scaffold_top_down_shooter_game" in PRODUCER.tool_set
    print("OK Producer allowlist exposes studio_scaffold_top_down_shooter_game")


def test_shooter_scaffolder_not_available_to_specialists() -> None:
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
        assert "studio_scaffold_top_down_shooter_game" not in role.tool_set, (
            f"{role.id} must not call the shooter scaffolder"
        )
    print("OK only Producer can scaffold a top-down shooter; specialists cannot")


def run_test() -> None:
    # Validation
    test_shooter_scaffold_rejects_zero_kills()
    test_shooter_scaffold_rejects_too_many_kills()
    test_shooter_scaffold_rejects_zero_interval()
    test_shooter_scaffold_rejects_huge_max_alive()
    test_shooter_scaffold_rejects_negative_play_area()
    # Happy path
    test_shooter_scaffold_creates_milestone_and_tasks()
    test_shooter_scaffold_covers_action_specialist_roles()
    test_shooter_worker_task_embeds_combat_template_recipe()
    test_shooter_worker_task_passes_through_scaffold_params()
    test_shooter_ui_builder_task_uses_lives_token()
    test_shooter_material_artist_uses_emission_for_projectile()
    test_shooter_localization_includes_lose_screen()
    test_shooter_game_balancer_task_references_balance_audit()
    test_shooter_marketing_normalises_bundle_id()
    # Producer surface
    test_producer_can_call_shooter_scaffolder()
    test_shooter_scaffolder_not_available_to_specialists()
    print("All Phase 44 shooter-scaffold tests passed")


if __name__ == "__main__":
    run_test()
