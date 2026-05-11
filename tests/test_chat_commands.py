"""Phase 59 tests: deterministic slash-command dispatch.

The chat REPL routes /<command> through chat_commands.dispatch().
This module is the testable core — no rich output, just returns
a CommandResult triple. Verify:
- Every known command is recognised
- Every known command actually fires the right tool
- Unknown commands fall through unrecognised
- Args parse correctly (genre alias, multi-word names with quotes,
  flags, numeric args)
- Error paths return ok=False without crashing
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.cli.chat_commands import CommandResult, dispatch
from unitytools.studio import StudioPaths, StudioState, init_studio_tools


def _fresh_studio_cwd() -> tuple[StudioState, Path, str]:
    """Create a fresh studio + cd into its root. Returns the
    state, the tmpdir Path, and the previous cwd to restore."""
    prev_cwd = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="chat-cmd-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    paths.gdd.write_text("# GDD\nA pitch.\n", encoding="utf-8")
    os.chdir(tmp)
    return state, tmp, prev_cwd


# ─────────────────────────────────────────── quit / unknown / empty


def test_empty_line_returns_not_handled() -> None:
    r = dispatch("")
    assert r.handled is False
    print("OK empty line -> handled=False (so REPL falls through)")


def test_unknown_command_returns_not_handled() -> None:
    r = dispatch("not_a_command foo bar")
    assert r.handled is False
    print("OK unknown command -> handled=False (REPL prints help)")


def test_quit_returns_handled_with_quit_flag() -> None:
    for word in ("quit", "exit", "q"):
        r = dispatch(word)
        assert r.handled is True
        assert r.quit is True
        assert "Goodbye" in r.message
    print("OK quit/exit/q all return quit=True")


# ─────────────────────────────────────────── scaffold


def test_scaffold_collectathon_opens_13_tasks() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("scaffold collectathon Coin Hunter")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_scaffold_collectathon_game"
        assert "13 tasks" in r.message or "task" in r.message.lower()
        # The actual studio state has the tasks now
        assert len(state.load_tasks()) == 13
    finally:
        os.chdir(prev)
    print("OK /scaffold collectathon -> studio_scaffold_collectathon_game fired, 13 tasks landed")


def test_scaffold_recognises_genre_aliases() -> None:
    """Test that 'collect' = 'collectathon', 'wave' = 'shooter',
    'jump' = 'platformer', 'endless' = 'runner'."""
    aliases = {
        "collect": "studio_scaffold_collectathon_game",
        "wave": "studio_scaffold_top_down_shooter_game",
        "topdown": "studio_scaffold_top_down_shooter_game",
        "endless": "studio_scaffold_endless_runner_game",
        "runner": "studio_scaffold_endless_runner_game",
        "jump": "studio_scaffold_platformer_game",
        "platform": "studio_scaffold_platformer_game",
    }
    for alias, expected_tool in aliases.items():
        _, _, prev = _fresh_studio_cwd()
        try:
            r = dispatch(f"scaffold {alias}")
            assert r.handled is True
            assert r.ok is True, f"alias {alias!r} failed: {r.message}"
            assert r.tool_name == expected_tool, (
                f"alias {alias!r} routed to {r.tool_name}, expected {expected_tool}"
            )
        finally:
            os.chdir(prev)
    print(f"OK all 7 genre aliases route correctly to scaffolders")


def test_scaffold_missing_genre_returns_usage() -> None:
    r = dispatch("scaffold")
    assert r.handled is True
    assert r.ok is False
    assert "Usage" in r.message
    print("OK /scaffold without genre -> usage hint")


def test_scaffold_unknown_genre_lists_choices() -> None:
    r = dispatch("scaffold zorblax")
    assert r.handled is True
    assert r.ok is False
    assert "zorblax" in r.message.lower()
    assert "collectathon" in r.message or "shooter" in r.message
    print("OK unknown genre -> error message lists valid choices")


def test_scaffold_multi_word_name_with_quotes() -> None:
    """`scaffold platformer "Hop Quest Deluxe"` should keep the name intact."""
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch('scaffold platformer "Hop Quest Deluxe"')
        assert r.handled is True
        assert r.ok is True
        # The milestone name carries the game name
        ms = state.load_milestones()
        assert len(ms) == 1
        assert "Hop Quest Deluxe" in ms[0].name
    finally:
        os.chdir(prev)
    print("OK quoted multi-word game name preserved through scaffolder")


def test_scaffold_multi_word_name_without_quotes() -> None:
    """Without quotes, remaining args are joined."""
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("scaffold collectathon Star Catcher Pro")
        assert r.handled is True
        ms = state.load_milestones()
        assert "Star Catcher Pro" in ms[0].name
    finally:
        os.chdir(prev)
    print("OK unquoted multi-word name reassembled by join")


# ─────────────────────────────────────────── dashboard


def test_dashboard_basic_call() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("dashboard")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_dashboard"
        assert "Dashboard" in r.message
    finally:
        os.chdir(prev)
    print("OK /dashboard fires studio_dashboard")


def test_dashboard_save_flag_writes_to_reviews() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("dashboard --save")
        assert r.handled is True
        assert r.ok is True
        # The result dict carries the saved_path
        saved = r.tool_result.get("saved_path") if r.tool_result else None
        assert saved is not None
        assert Path(saved).exists()
    finally:
        os.chdir(prev)
    print("OK /dashboard --save writes report to studio/reviews/")


def test_dashboard_days_arg_parsed() -> None:
    """Both '--days 14' and bare '14' should set days=14."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r1 = dispatch("dashboard --days 14")
        assert r1.tool_result.get("days") == 14
        r2 = dispatch("dashboard 14")
        assert r2.tool_result.get("days") == 14
    finally:
        os.chdir(prev)
    print("OK /dashboard accepts both '--days N' and bare 'N'")


# ─────────────────────────────────────────── ship / cost / audit / tasks


def test_ship_runs_readiness_check() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("ship")
        assert r.handled is True
        assert r.tool_name == "studio_ship_readiness_check"
        assert "verdict" in r.message
    finally:
        os.chdir(prev)
    print("OK /ship runs studio_ship_readiness_check")


def test_cost_runs_summary_with_default_window() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("cost")
        assert r.handled is True
        assert r.tool_name == "studio_cost_summary"
        assert "USD" in r.message
        # Default window is 7 days
        assert r.tool_result.get("days") == 7
    finally:
        os.chdir(prev)
    print("OK /cost defaults to 7-day window")


def test_cost_accepts_numeric_window() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("cost 30")
        assert r.tool_result.get("days") == 30
    finally:
        os.chdir(prev)
    print("OK /cost 30 sets window to 30 days")


def test_audit_routes_each_kind_to_correct_tool() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        # Engine-gated audits need a bridge; consistency works offline
        r = dispatch("audit consistency")
        assert r.handled is True
        assert r.tool_name == "studio_internal_consistency_check"
        r = dispatch("audit ship")
        assert r.tool_name == "studio_ship_readiness_check"
        r = dispatch("audit balance")
        assert r.tool_name == "studio_balance_audit"
        r = dispatch("audit localization")
        assert r.tool_name == "studio_localization_audit"
    finally:
        os.chdir(prev)
    print("OK /audit routes consistency / ship / balance / localization to right tools")


def test_audit_aliases_route_correctly() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        # 'drift' aliases consistency, 'release' aliases ship,
        # 'playtest' aliases balance, 'locale' aliases localization
        assert dispatch("audit drift").tool_name == "studio_internal_consistency_check"
        assert dispatch("audit release").tool_name == "studio_ship_readiness_check"
        assert dispatch("audit playtest").tool_name == "studio_balance_audit"
        assert dispatch("audit locale").tool_name == "studio_localization_audit"
        assert dispatch("audit sky").tool_name == "studio_atmosphere_audit"
        assert dispatch("audit fog").tool_name == "studio_atmosphere_audit"
        assert dispatch("audit particle").tool_name == "studio_vfx_audit"
    finally:
        os.chdir(prev)
    print("OK audit aliases (drift/release/playtest/locale/sky/fog/particle) route correctly")


def test_audit_missing_kind_returns_usage() -> None:
    r = dispatch("audit")
    assert r.handled is True
    assert r.ok is False
    assert "Usage" in r.message
    print("OK /audit without kind -> usage hint")


def test_audit_unknown_kind_lists_choices() -> None:
    r = dispatch("audit zorblax")
    assert r.handled is True
    assert r.ok is False
    assert "zorblax" in r.message.lower()
    print("OK unknown audit kind -> error lists valid choices")


def test_tasks_lists_backlog() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        # Seed via the scaffolder
        dispatch("scaffold collectathon X")
        r = dispatch("tasks")
        assert r.handled is True
        assert r.tool_name == "studio_list_tasks"
        assert "13" in r.message
    finally:
        os.chdir(prev)
    print("OK /tasks lists all backlog tasks (13 after collectathon scaffold)")


def test_tasks_with_status_filter() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("scaffold collectathon X")
        r = dispatch("tasks pending")
        assert r.handled is True
        assert r.tool_result.get("count") == 13   # all start pending
        r = dispatch("tasks done")
        assert r.tool_result.get("count") == 0
    finally:
        os.chdir(prev)
    print("OK /tasks <status> filters by status (pending=13, done=0 fresh)")


def test_milestones_command() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("scaffold collectathon X")
        r = dispatch("milestones")
        assert r.handled is True
        assert r.tool_name == "studio_list_milestones"
        assert "1" in r.message  # one milestone created by scaffolder
    finally:
        os.chdir(prev)
    print("OK /milestones lists milestones (1 after scaffold)")


def test_ms_alias_for_milestones() -> None:
    """Short alias."""
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("scaffold collectathon X")
        r = dispatch("ms")
        assert r.handled is True
        assert r.tool_name == "studio_list_milestones"
    finally:
        os.chdir(prev)
    print("OK /ms alias works for /milestones")


def test_decisions_command() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("decisions")
        assert r.handled is True
        assert r.tool_name == "studio_list_decisions"
    finally:
        os.chdir(prev)
    print("OK /decisions lists decisions")


# ─────────────────────────────────────────── argument parsing


def test_dispatcher_handles_mismatched_quotes() -> None:
    """A user typing `scaffold collectathon "broken quote` shouldn't crash."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch('scaffold collectathon "broken')
        # Should fall back to whitespace split and still try the scaffold
        assert r.handled is True
        # It might succeed (name="\"broken") or fail; either way no crash
    finally:
        os.chdir(prev)
    print("OK mismatched quotes degrade gracefully (no crash)")


def test_command_lower_case() -> None:
    """Commands are case-insensitive."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r1 = dispatch("Ship")
        r2 = dispatch("SHIP")
        r3 = dispatch("ship")
        for r in (r1, r2, r3):
            assert r.handled is True
            assert r.tool_name == "studio_ship_readiness_check"
    finally:
        os.chdir(prev)
    print("OK command name is case-insensitive")


def run_test() -> None:
    # Plumbing
    test_empty_line_returns_not_handled()
    test_unknown_command_returns_not_handled()
    test_quit_returns_handled_with_quit_flag()
    # Scaffold
    test_scaffold_collectathon_opens_13_tasks()
    test_scaffold_recognises_genre_aliases()
    test_scaffold_missing_genre_returns_usage()
    test_scaffold_unknown_genre_lists_choices()
    test_scaffold_multi_word_name_with_quotes()
    test_scaffold_multi_word_name_without_quotes()
    # Dashboard
    test_dashboard_basic_call()
    test_dashboard_save_flag_writes_to_reviews()
    test_dashboard_days_arg_parsed()
    # Ship + cost + audit + tasks + milestones + decisions
    test_ship_runs_readiness_check()
    test_cost_runs_summary_with_default_window()
    test_cost_accepts_numeric_window()
    test_audit_routes_each_kind_to_correct_tool()
    test_audit_aliases_route_correctly()
    test_audit_missing_kind_returns_usage()
    test_audit_unknown_kind_lists_choices()
    test_tasks_lists_backlog()
    test_tasks_with_status_filter()
    test_milestones_command()
    test_ms_alias_for_milestones()
    test_decisions_command()
    # Arg parsing
    test_dispatcher_handles_mismatched_quotes()
    test_command_lower_case()
    print("All Phase 59 chat-command tests passed")


if __name__ == "__main__":
    run_test()
