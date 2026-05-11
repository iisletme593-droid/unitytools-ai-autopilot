"""Phase 55 tests: Storyteller role + dialog tools + DialogText runtime.

Covers: dialog_id validation, read/write round-trip across multiple
dialogs, list_dialogs inventory, malformed-file tolerance, role
allowlist isolation, Worker read access, dispatch routing.
"""
from __future__ import annotations

import json
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
    STORYTELLER,
    StudioPaths,
    StudioState,
    TUTORIAL_DESIGNER,
    UI_BUILDER,
    VFX_DIRECTOR,
    WORKER,
    init_studio_tools,
)
from unitytools.studio.tools import (
    studio_list_dialogs,
    studio_read_dialog,
    studio_write_dialog,
)


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="storyteller-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ───────────────────────────────────────────── path + dir


def test_paths_expose_dialogs_dir() -> None:
    state, _ = _fresh_studio()
    assert state.paths.dialogs.name == "dialogs"
    assert state.paths.dialogs.parent == state.paths.root
    # all_dirs() includes it so studio-init scaffolds the dir
    assert state.paths.dialogs in state.paths.all_dirs()
    print("OK StudioPaths.dialogs -> studio/dialogs/, in all_dirs() for studio-init")


# ───────────────────────────────────────────── dialog_id validation


def test_write_dialog_rejects_invalid_ids() -> None:
    _fresh_studio()
    for bad in ("Intro", "intro-1", "intro/sub", "1intro", "", "intro.json",
                 "A" * 50, "intro 1"):
        result = studio_write_dialog(dialog_id=bad, lines=["a"])
        assert result["ok"] is False, f"dialog_id {bad!r} should have been rejected"
        assert "dialog_id" in result["error"]
    print("OK invalid dialog_ids rejected (uppercase, hyphens, slashes, starts-with-digit, empty, with extension, too long, with space)")


def test_write_dialog_accepts_valid_ids() -> None:
    _fresh_studio()
    for good in ("intro", "win", "boss_intro", "cave_entrance",
                  "level_1_outro", "a", "i_n_t_r_o_99"):
        result = studio_write_dialog(dialog_id=good, lines=[f"hi from {good}"])
        assert result["ok"] is True, f"dialog_id {good!r} should have been accepted"
    print("OK valid dialog_ids accepted (lowercase, underscores, digits, mixed)")


def test_write_dialog_rejects_non_string_lines() -> None:
    _fresh_studio()
    result = studio_write_dialog(dialog_id="intro", lines=["hello", 42, "world"])
    assert result["ok"] is False
    assert "string" in result["error"].lower()
    print("OK non-string entries in lines rejected")


def test_write_dialog_rejects_non_list_lines() -> None:
    _fresh_studio()
    result = studio_write_dialog(dialog_id="intro", lines="not a list")  # type: ignore[arg-type]
    assert result["ok"] is False
    print("OK non-list lines argument rejected")


# ───────────────────────────────────────────── read / write round-trip


def test_read_dialog_returns_empty_when_absent() -> None:
    _fresh_studio()
    result = studio_read_dialog(dialog_id="intro")
    assert result["ok"] is True
    assert result["lines"] == []
    print("OK read_dialog: empty list when file absent")


def test_write_then_read_dialog_round_trip() -> None:
    state, _ = _fresh_studio()
    lines = ["Welcome to the cave.", "Watch your step.", "Coins await."]
    write_result = studio_write_dialog(dialog_id="cave_intro", lines=lines)
    assert write_result["ok"] is True
    assert write_result["line_count"] == 3
    assert (state.paths.dialogs / "cave_intro.json").exists()
    read_result = studio_read_dialog(dialog_id="cave_intro")
    assert read_result["lines"] == lines
    assert read_result["line_count"] == 3
    print("OK dialog write then read round-trips")


def test_write_dialog_handles_unicode_and_emoji() -> None:
    """Turkish / accented + emoji should round-trip cleanly. JSON written
    with ensure_ascii=False so the actual chars are in the file."""
    state, _ = _fresh_studio()
    studio_write_dialog(dialog_id="tr_intro", lines=[
        "Şato'ya hoş geldin.", "Dikkatli ol, dostum.", "İyi şanslar! 🎮",
    ])
    raw = (state.paths.dialogs / "tr_intro.json").read_text(encoding="utf-8")
    assert "Şato" in raw
    assert "🎮" in raw
    result = studio_read_dialog(dialog_id="tr_intro")
    assert result["lines"][2] == "İyi şanslar! 🎮"
    print("OK Unicode + emoji round-trip cleanly")


def test_read_dialog_handles_malformed_file() -> None:
    state, _ = _fresh_studio()
    state.paths.dialogs.mkdir(parents=True, exist_ok=True)
    (state.paths.dialogs / "broken.json").write_text("not valid json", encoding="utf-8")
    result = studio_read_dialog(dialog_id="broken")
    assert result["ok"] is False
    assert "malformed" in result["error"].lower() or "json" in result["error"].lower()
    print("OK malformed dialog file -> clean error")


def test_read_dialog_rejects_non_array_payload() -> None:
    """A JSON object instead of array should error cleanly."""
    state, _ = _fresh_studio()
    state.paths.dialogs.mkdir(parents=True, exist_ok=True)
    (state.paths.dialogs / "wrong_shape.json").write_text(
        json.dumps({"line_1": "hello"}), encoding="utf-8")
    result = studio_read_dialog(dialog_id="wrong_shape")
    assert result["ok"] is False
    assert "array" in result["error"].lower()
    print("OK JSON-but-not-array dialog file -> clean error")


def test_write_dialog_overwrites() -> None:
    """Unlike strings (merge mode), dialogs are always full replace —
    the lines are an ordered narrative, not a key-value bag."""
    _fresh_studio()
    studio_write_dialog(dialog_id="intro", lines=["a", "b", "c"])
    studio_write_dialog(dialog_id="intro", lines=["x", "y"])
    result = studio_read_dialog(dialog_id="intro")
    assert result["lines"] == ["x", "y"]
    print("OK write_dialog is full replace (ordered narrative semantics)")


# ───────────────────────────────────────────── list_dialogs


def test_list_dialogs_empty_dir() -> None:
    _fresh_studio()
    result = studio_list_dialogs()
    assert result["ok"] is True
    assert result["count"] == 0
    print("OK list_dialogs: zero count when dir empty")


def test_list_dialogs_returns_each_with_line_count() -> None:
    _fresh_studio()
    studio_write_dialog(dialog_id="intro", lines=["a", "b"])
    studio_write_dialog(dialog_id="win", lines=["w"])
    studio_write_dialog(dialog_id="game_over", lines=["o", "v", "e", "r"])
    result = studio_list_dialogs()
    assert result["count"] == 3
    rows = {r["dialog_id"]: r["line_count"] for r in result["dialogs"]}
    assert rows == {"intro": 2, "win": 1, "game_over": 4}
    print("OK list_dialogs returns each dialog + line count")


# ───────────────────────────────────────────── role allowlist


def test_storyteller_allowlist() -> None:
    assert "studio_list_dialogs" in STORYTELLER.tool_set
    assert "studio_read_dialog" in STORYTELLER.tool_set
    assert "studio_write_dialog" in STORYTELLER.tool_set
    # Reads adjacent context for tone + scene awareness
    assert "studio_read_gdd" in STORYTELLER.tool_set
    assert "studio_read_scene_catalog" in STORYTELLER.tool_set
    assert "studio_read_press_kit" in STORYTELLER.tool_set
    # Lifecycle + escalation
    assert "studio_update_task_status" in STORYTELLER.tool_set
    assert "studio_add_task" in STORYTELLER.tool_set
    assert "studio_propose_decision" in STORYTELLER.tool_set
    # Cannot write any OTHER doc (each doc role owns its surface)
    for tool in ("studio_write_gdd", "studio_write_art_bible",
                  "studio_write_audio_brief", "studio_write_press_kit",
                  "studio_write_tutorial", "studio_write_scene_catalog",
                  "studio_write_achievements", "studio_write_strings"):
        assert tool not in STORYTELLER.tool_set, (
            f"Storyteller must not have {tool}"
        )
    # Cannot mutate scene
    assert "unity_create_primitive" not in STORYTELLER.tool_set
    assert "unity_attach_behaviour" not in STORYTELLER.tool_set
    print("OK Storyteller allowlist: dialog r/w + 3 context reads + tasks/decisions, NOTHING ELSE")


def test_other_roles_lack_dialog_write() -> None:
    """Only Storyteller writes dialog files."""
    for role in (ACHIEVEMENT_DESIGNER, ART_DIRECTOR, ATMOSPHERE_DIRECTOR,
                  AUDIO_DIRECTOR, BUILD_ENGINEER, CAMERA_DIRECTOR, DESIGNER,
                  GAME_BALANCER, LIGHTING_DIRECTOR, LOCALIZATION_LEAD,
                  MARKETING_DIRECTOR, MATERIAL_ARTIST, PHYSICS_QA,
                  SCENE_DIRECTOR, TUTORIAL_DESIGNER, UI_BUILDER,
                  VFX_DIRECTOR, WORKER):
        assert "studio_write_dialog" not in role.tool_set, (
            f"{role.id} must not write dialog files"
        )
    print("OK only Storyteller writes dialog files")


def test_worker_reads_dialog_inventory() -> None:
    """The Worker attaches DialogText components and needs to know
    what dialog_ids exist + their content. READ-only access."""
    assert "studio_list_dialogs" in WORKER.tool_set
    assert "studio_read_dialog" in WORKER.tool_set
    assert "studio_write_dialog" not in WORKER.tool_set
    print("OK Worker reads (but does not write) the dialog inventory")


def test_storyteller_doc_only_no_engine() -> None:
    assert STORYTELLER.needs_engine is False
    assert STORYTELLER.needs_vision is False
    print("OK Storyteller is engine-free + vision-free (doc-only)")


# ───────────────────────────────────────────── dispatch routing


def test_dispatch_map_routes_storyteller_to_self() -> None:
    assert DISPATCH_MAP["storyteller"] == "storyteller"
    print("OK DISPATCH_MAP[storyteller] -> storyteller")


def test_storyteller_in_roles_validation_tuple() -> None:
    from unitytools.studio.models import ROLES
    assert "storyteller" in ROLES, (
        "storyteller must be in ROLES so studio_add_task accepts it"
    )
    print("OK storyteller is in ROLES validation tuple")


def test_existing_routes_unchanged() -> None:
    assert DISPATCH_MAP["designer"] == "designer"
    assert DISPATCH_MAP["tutorial_designer"] == "tutorial_designer"
    assert DISPATCH_MAP["achievement_designer"] == "achievement_designer"
    assert DISPATCH_MAP["scene_director"] == "scene_director"
    assert DISPATCH_MAP["producer"] is None
    print("OK existing DISPATCH_MAP rules unchanged after storyteller addition")


def run_test() -> None:
    # Path + dir
    test_paths_expose_dialogs_dir()
    # Validation
    test_write_dialog_rejects_invalid_ids()
    test_write_dialog_accepts_valid_ids()
    test_write_dialog_rejects_non_string_lines()
    test_write_dialog_rejects_non_list_lines()
    # Read / write
    test_read_dialog_returns_empty_when_absent()
    test_write_then_read_dialog_round_trip()
    test_write_dialog_handles_unicode_and_emoji()
    test_read_dialog_handles_malformed_file()
    test_read_dialog_rejects_non_array_payload()
    test_write_dialog_overwrites()
    # list_dialogs
    test_list_dialogs_empty_dir()
    test_list_dialogs_returns_each_with_line_count()
    # Role + dispatch
    test_storyteller_allowlist()
    test_other_roles_lack_dialog_write()
    test_worker_reads_dialog_inventory()
    test_storyteller_doc_only_no_engine()
    test_dispatch_map_routes_storyteller_to_self()
    test_storyteller_in_roles_validation_tuple()
    test_existing_routes_unchanged()
    print("All Phase 55 storyteller tests passed")


if __name__ == "__main__":
    run_test()
