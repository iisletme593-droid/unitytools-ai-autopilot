"""Phase 42 tests: studio_scaffold_collectathon_game.

One Producer call should land a milestone + a structured backlog
covering every specialist role needed to ship a complete collectathon
MVP. We verify the call validates inputs, creates a single milestone,
opens tasks for each of the expected roles, links every task to the
milestone, and embeds the right Behaviour Library wiring in task
descriptions.
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
from unitytools.studio.tools import studio_scaffold_collectathon_game


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="scaffold-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── validation


def test_scaffold_rejects_zero_coin_count() -> None:
    _fresh_studio()
    result = studio_scaffold_collectathon_game(coin_count=0)
    assert result["ok"] is False
    assert "coin_count" in result["error"]
    print("OK coin_count=0 rejected")


def test_scaffold_rejects_too_many_coins() -> None:
    _fresh_studio()
    result = studio_scaffold_collectathon_game(coin_count=500)
    assert result["ok"] is False
    assert "coin_count" in result["error"]
    print("OK coin_count=500 (>100) rejected")


def test_scaffold_rejects_huge_play_area() -> None:
    _fresh_studio()
    result = studio_scaffold_collectathon_game(play_area_radius=999.0)
    assert result["ok"] is False
    assert "play_area_radius" in result["error"]
    print("OK play_area_radius>50 rejected")


def test_scaffold_rejects_negative_play_area() -> None:
    _fresh_studio()
    result = studio_scaffold_collectathon_game(play_area_radius=-1.0)
    assert result["ok"] is False
    print("OK negative play_area_radius rejected")


# ───────────────────────────────────────────── happy path


def test_scaffold_happy_path_creates_milestone_plus_tasks() -> None:
    state, _ = _fresh_studio()
    result = studio_scaffold_collectathon_game(
        game_name="Coin Hunter",
        coin_count=8,
        play_area_radius=6.0,
    )
    assert result["ok"] is True
    assert result["game_name"] == "Coin Hunter"
    assert result["coin_count"] == 8

    # Milestone exists in state
    milestones = state.load_milestones()
    assert len(milestones) == 1
    assert milestones[0].id == result["milestone_id"]
    assert "Coin Hunter" in milestones[0].name

    # Tasks landed in the backlog and link to the milestone
    tasks = state.load_tasks()
    assert len(tasks) == result["task_count"]
    assert len(tasks) >= 10, f"expected >= 10 scaffolded tasks; got {len(tasks)}"
    for t in tasks:
        assert t.milestone == result["milestone_id"], (
            f"task {t.title!r} should link to the scaffolded milestone"
        )
    print(f"OK scaffold opens {len(tasks)} tasks all linked to one milestone")


def test_scaffold_covers_full_specialist_pipeline() -> None:
    """Every role in the studio's specialist pipeline should be touched
    by the scaffolder so the dispatcher can actually run the whole thing
    end to end."""
    _fresh_studio()
    result = studio_scaffold_collectathon_game()
    roles = {t["role"] for t in result["tasks"]}

    # The minimum set we need for an end-to-end collectathon MVP
    must_have = {
        "designer",           # GDD
        "art_director",       # Art Bible
        "worker",             # scene placement
        "ui_builder",         # HUD + pause canvas
        "lighting_director",  # light the playfield
        "atmosphere_director",# skybox + fog
        "camera_director",    # framing
        "audio_director",     # audio brief
        "localization_lead",  # string tables
        "marketing_director", # press kit + PlayerSettings
        "playtester",         # smoke test
        "build_engineer",     # ship binary
    }
    missing = must_have - roles
    assert not missing, f"scaffold missing tasks for roles: {missing}"
    print(f"OK scaffold covers all 12 critical specialist roles ({len(roles)} unique)")


def test_scaffold_worker_task_embeds_behaviour_library_calls() -> None:
    """The Worker task's description must reference the Behaviour Library
    primitives by name so the running Worker can copy them verbatim
    without inventing new behaviours."""
    _fresh_studio()
    result = studio_scaffold_collectathon_game(coin_count=5)
    worker_task = next(t for t in result["tasks"] if t["role"] == "worker")
    # Pull the full task back from state so we get the description
    state, _ = _fresh_studio()
    # Re-run to get tasks in a fresh state
    result2 = studio_scaffold_collectathon_game(coin_count=5)
    tasks = state.load_tasks()
    worker_full = next(t for t in tasks if t.role == "worker")
    body = worker_full.description
    # Worker should know about: snapshot, KeyboardMover, GameSession,
    # Collectible (with playerFilter), Rotator on coins, save_scene
    assert "unity_create_scene_snapshot" in body
    assert "KeyboardMover" in body
    assert "GameSession" in body
    assert "Collectible" in body
    assert "playerFilter" in body
    assert "Rotator" in body
    assert "unity_save_scene" in body
    print("OK Worker task description embeds Behaviour Library wiring")


def test_scaffold_ui_builder_task_wires_hud_and_pause() -> None:
    """UI Builder task should reference ScoreHUD + PauseMenu + SettingsStore
    (Phases 40-41 game-loop primitives)."""
    state, _ = _fresh_studio()
    studio_scaffold_collectathon_game()
    ui_task = next(t for t in state.load_tasks() if t.role == "ui_builder")
    for primitive in ("ScoreHUD", "PauseMenu", "SettingsStore",
                       "unity_create_ui_canvas", "unity_create_ui_text"):
        assert primitive in ui_task.description, f"UI Builder task missing {primitive}"
    print("OK UI Builder task references ScoreHUD/PauseMenu/SettingsStore + canvas/text builders")


def test_scaffold_localization_task_seeds_en_and_tr() -> None:
    _fresh_studio()
    result = studio_scaffold_collectathon_game(game_name="My Game")
    loc_task_id = next(t["task_id"] for t in result["tasks"]
                       if t["role"] == "localization_lead")
    state, _ = _fresh_studio()
    studio_scaffold_collectathon_game(game_name="My Game")
    task = next(t for t in state.load_tasks() if t.role == "localization_lead")
    assert "'en'" in task.description and "'tr'" in task.description
    assert "title.main" in task.description
    assert "btn.start" in task.description
    print("OK localization task seeds en + tr with canonical keys")


def test_scaffold_marketing_uses_provided_game_name_for_bundle_id() -> None:
    state, _ = _fresh_studio()
    studio_scaffold_collectathon_game(game_name="Neon Drift")
    mkt = next(t for t in state.load_tasks() if t.role == "marketing_director")
    # bundle_id should be normalised (lowercase, spaces stripped)
    assert "com.unitytools.neondrift" in mkt.description
    assert "Neon Drift" in mkt.description
    print("OK marketing task carries normalised bundle_id from game_name")


def test_scaffold_passes_coin_count_into_win_condition() -> None:
    """winScore must equal the coin_count we asked for, so completing
    every coin = win."""
    state, _ = _fresh_studio()
    studio_scaffold_collectathon_game(coin_count=15)
    worker = next(t for t in state.load_tasks() if t.role == "worker")
    assert "winScore=15" in worker.description
    print("OK Worker task hard-codes winScore=coin_count")


# ───────────────────────────────────────────── Producer access


def test_producer_can_call_scaffold() -> None:
    assert "studio_scaffold_collectathon_game" in PRODUCER.tool_set
    print("OK Producer allowlist exposes studio_scaffold_collectathon_game")


def test_scaffold_not_available_to_other_roles() -> None:
    """Only the Producer drives the meta-loop; specialists execute their
    own scoped tasks. Don't let any specialist call the scaffolder."""
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
        assert "studio_scaffold_collectathon_game" not in role.tool_set, (
            f"{role.id} must not call the game scaffolder — that's Producer's job"
        )
    print("OK only Producer can call the scaffolder; specialists cannot")


# ───────────────────────────────────────────── ROLES tuple (Phase 42 fix)


def test_all_dispatch_roles_in_validation_tuple() -> None:
    """Bug fix carried by this phase: ROLES tuple in models.py was stale
    and excluded specialists like atmosphere_director, marketing_director,
    etc. studio_add_task would reject tasks for them. Verify that's
    fixed."""
    from unitytools.studio import DISPATCH_MAP
    from unitytools.studio.models import ROLES
    for dispatch_key in DISPATCH_MAP.keys():
        # The dispatch tuple includes both originating role IDs (e.g.
        # qa) and target IDs (e.g. playtester). Originating roles are
        # what studio_add_task validates against — the DISPATCH_MAP keys
        # IS the originating set.
        assert dispatch_key in ROLES, (
            f"role {dispatch_key!r} routes in DISPATCH_MAP but isn't in "
            f"ROLES — studio_add_task would reject it."
        )
    print(f"OK every DISPATCH_MAP key ({len(DISPATCH_MAP)} entries) is in ROLES validation tuple")


def run_test() -> None:
    # Validation
    test_scaffold_rejects_zero_coin_count()
    test_scaffold_rejects_too_many_coins()
    test_scaffold_rejects_huge_play_area()
    test_scaffold_rejects_negative_play_area()
    # Happy path
    test_scaffold_happy_path_creates_milestone_plus_tasks()
    test_scaffold_covers_full_specialist_pipeline()
    test_scaffold_worker_task_embeds_behaviour_library_calls()
    test_scaffold_ui_builder_task_wires_hud_and_pause()
    test_scaffold_localization_task_seeds_en_and_tr()
    test_scaffold_marketing_uses_provided_game_name_for_bundle_id()
    test_scaffold_passes_coin_count_into_win_condition()
    # Role surface
    test_producer_can_call_scaffold()
    test_scaffold_not_available_to_other_roles()
    # Bug fix carried by this phase
    test_all_dispatch_roles_in_validation_tuple()
    print("All Phase 42 scaffolder tests passed")


if __name__ == "__main__":
    run_test()
