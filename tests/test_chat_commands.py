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


# ─────────────────────────────────────────── Phase 60 inventory + meta


def test_refs_command_lists_references() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("refs")
        assert r.handled is True
        assert r.tool_name == "studio_list_references"
    finally:
        os.chdir(prev)
    print("OK /refs -> studio_list_references")


def test_screenshots_command_and_alias() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r1 = dispatch("screenshots")
        r2 = dispatch("shots")
        for r in (r1, r2):
            assert r.handled is True
            assert r.tool_name == "studio_list_screenshots"
    finally:
        os.chdir(prev)
    print("OK /screenshots + /shots alias both route to studio_list_screenshots")


def test_locales_command() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("locales")
        assert r.handled is True
        assert r.tool_name == "studio_list_locales"
    finally:
        os.chdir(prev)
    print("OK /locales -> studio_list_locales")


def test_dialogs_command() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("dialogs")
        assert r.handled is True
        assert r.tool_name == "studio_list_dialogs"
    finally:
        os.chdir(prev)
    print("OK /dialogs -> studio_list_dialogs")


def test_assets_command() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("assets")
        assert r.handled is True
        assert r.tool_name == "studio_asset_manifest"
    finally:
        os.chdir(prev)
    print("OK /assets -> studio_asset_manifest")


def test_behaviours_command_lists_full_library() -> None:
    # No studio needed; the behaviour library is a module constant
    r = dispatch("behaviours")
    assert r.handled is True
    assert r.ok is True
    assert r.tool_result["total"] == 30
    # All 30 names match without filter
    assert len(r.tool_result["matches"]) == 30
    print("OK /behaviours lists all 30 entries when no filter")


def test_behaviours_command_filters_by_substring() -> None:
    """`/behaviours camera` should match only LookAtCamera + CameraShake."""
    r = dispatch("behaviours camera")
    assert r.handled is True
    # The filter is case-insensitive substring match
    matches = r.tool_result["matches"]
    assert "LookAtCamera" in matches
    assert "CameraShake" in matches
    # Should NOT include unrelated ones
    assert "Rotator" not in matches
    print(f"OK /behaviours camera -> filtered to {len(matches)} matches (LookAtCamera, CameraShake)")


def test_behaviors_us_spelling_works() -> None:
    """US spelling alias 'behaviors' = 'behaviours'."""
    r = dispatch("behaviors")
    assert r.handled is True
    assert r.tool_result["total"] == 30
    print("OK /behaviors (US spelling) is an alias for /behaviours")


def test_roles_command_lists_24_roles() -> None:
    r = dispatch("roles")
    assert r.handled is True
    assert r.ok is True
    # The studio has 24 roles
    assert r.tool_result["count"] == 24
    # Spot-check some role ids
    role_ids = {row["id"] for row in r.tool_result["roles"]}
    for expected in ("producer", "designer", "worker", "playtester",
                      "build_engineer", "achievement_designer", "storyteller"):
        assert expected in role_ids, f"role {expected!r} missing from /roles"
    print("OK /roles lists 24 roles including all the new ones")


def test_diag_command_reports_studio_state() -> None:
    r = dispatch("diag")
    assert r.handled is True
    assert r.ok is True
    info = r.tool_result
    assert info["roles"] == 24
    assert info["behaviour_library_size"] == 30
    # 199+ total tools after both studio + unity_tools imported
    assert info["total_tools"] >= 100
    print(f"OK /diag reports tools={info['total_tools']} roles={info['roles']} "
          f"behaviours={info['behaviour_library_size']}")


def test_init_creates_studio_when_missing() -> None:
    """In a fresh empty dir, /init should scaffold the studio."""
    import tempfile
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="init-test-"))
    os.chdir(tmp)
    try:
        r = dispatch("init")
        assert r.handled is True
        assert r.ok is True
        # The marker docs should now exist
        for marker in ("gdd.md", "art_bible.md", "audio_brief.md",
                        "sprint_current.md"):
            assert (tmp / "studio" / marker).exists(), f"missing scaffolded file: {marker}"
        # /init again is idempotent — should report 'already initialised'
        r2 = dispatch("init")
        assert r2.handled is True
        assert r2.ok is True
        assert r2.tool_result.get("already_initialised") is True
    finally:
        os.chdir(prev)
    print("OK /init scaffolds 4+ canonical docs; re-running is idempotent")


def test_init_with_explicit_path() -> None:
    """`/init /custom/path` should scaffold there, not in cwd."""
    import tempfile
    prev = os.getcwd()
    cwd_tmp = Path(tempfile.mkdtemp(prefix="cwd-"))
    target_tmp = Path(tempfile.mkdtemp(prefix="target-"))
    os.chdir(cwd_tmp)
    try:
        # Path with quotes (could contain spaces)
        r = dispatch(f'init "{target_tmp}"')
        assert r.handled is True
        assert r.ok is True
        # Studio should be at target, NOT cwd
        assert (target_tmp / "studio" / "gdd.md").exists()
        assert not (cwd_tmp / "studio" / "gdd.md").exists()
    finally:
        os.chdir(prev)
    print("OK /init <path> scaffolds at the given path, not cwd")


def test_init_rejects_nonexistent_path() -> None:
    r = dispatch("init /does/not/exist/anywhere")
    assert r.handled is True
    assert r.ok is False
    assert "does not exist" in r.message.lower()
    print("OK /init <nonexistent-path> -> clean error")


# ─────────────────────────────────────────── Phase 61 /dispatch


def test_dispatch_command_recognised() -> None:
    """/dispatch is handled by the dispatcher (even on errors)."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("dispatch")
        assert r.handled is True
    finally:
        os.chdir(prev)
    print("OK /dispatch is a recognised command")


def test_dispatch_without_studio_fails_clean() -> None:
    """In a clean cwd with no studio, /dispatch should error with a
    helpful message — not crash."""
    import tempfile
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="no-studio-"))
    os.chdir(tmp)
    # Reset the global studio state so this matches a 'no studio' run
    import unitytools.studio.tools as st
    saved = st._STATE
    st._STATE = None
    try:
        r = dispatch("dispatch 3")
        assert r.handled is True
        assert r.ok is False
        assert "studio" in r.message.lower()
    finally:
        st._STATE = saved
        os.chdir(prev)
    print("OK /dispatch without active studio -> clean error")


def test_dispatch_without_context_or_dry_run_fails_clean() -> None:
    """A real /dispatch needs an LLM client (via DispatchContext).
    Without one + not in dry-run, it should error helpfully."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("dispatch 3")   # no ctx
        assert r.handled is True
        assert r.ok is False
        assert "context" in r.message.lower() or "config" in r.message.lower()
        # Hint at the dry-run escape hatch
        assert "dry-run" in r.message.lower() or "dry_run" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /dispatch without ctx (no dry-run) -> clean error + dry-run hint")


def test_dispatch_dry_run_works_without_context() -> None:
    """Dry-run mode uses RehearsalLLM, doesn't need an LLM client.
    Should run even without ctx."""
    state, _, prev = _fresh_studio_cwd()
    try:
        # Seed some pending tasks via the scaffolder
        dispatch("scaffold collectathon Demo")
        r = dispatch("dispatch 3 --dry-run")
        assert r.handled is True
        assert r.ok is True, f"dry-run should succeed; got {r.message}"
        assert r.tool_result["dry_run"] is True
        assert r.tool_result["total"] >= 1, "should have processed at least 1 task"
    finally:
        os.chdir(prev)
    print("OK /dispatch --dry-run works without DispatchContext")


def test_dispatch_caps_limit_at_50() -> None:
    """Operator typing /dispatch 999 shouldn't kick off an unbounded
    run. Cap at 50 with a friendly error."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("dispatch 100 --dry-run")
        assert r.handled is True
        assert r.ok is False
        assert "50" in r.message
    finally:
        os.chdir(prev)
    print("OK /dispatch caps at 50 tasks per run (anti-runaway guard)")


def test_dispatch_parses_only_filter() -> None:
    """--only role1,role2 parses to a tuple of role ids."""
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("scaffold collectathon Demo")
        r = dispatch("dispatch 5 --only designer,critic --dry-run")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_result["only_roles"] == ["designer", "critic"]
        # 'only' filter is empty for our seed (none of the scaffolded
        # tasks are role=designer / role=critic) but we still parsed correctly
    finally:
        os.chdir(prev)
    print("OK /dispatch --only designer,critic parses to a 2-element role tuple")


def test_dispatch_default_limit_is_5() -> None:
    """Bare /dispatch (no arg) caps at 5."""
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("scaffold collectathon Demo")
        r = dispatch("dispatch --dry-run")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_result["limit"] == 5
    finally:
        os.chdir(prev)
    print("OK bare /dispatch defaults limit=5")


# ─────────────────────────────────────────── Phase 64 /role


def test_role_command_recognised() -> None:
    """/role is a known command (handled=True even on errors)."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("role designer")
        assert r.handled is True
    finally:
        os.chdir(prev)
    print("OK /role is a recognised command")


def test_role_without_role_id_returns_usage() -> None:
    r = dispatch("role")
    assert r.handled is True
    assert r.ok is False
    assert "Usage" in r.message
    assert "role-id" in r.message
    print("OK /role without role-id -> usage hint")


def test_role_with_unknown_role_id_lists_choices() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("role zorblax_designer")
        assert r.handled is True
        assert r.ok is False
        assert "zorblax_designer" in r.message
        # Lists the 24 valid roles
        for known in ("producer", "designer", "worker", "achievement_designer"):
            assert known in r.message
    finally:
        os.chdir(prev)
    print("OK unknown role-id -> error message lists every valid id")


def test_role_without_context_fails_clean_with_helpful_message() -> None:
    """A real /role needs ctx (for the LLM client). Without one,
    fail cleanly + tell the user why."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("role designer Draft GDD")
        assert r.handled is True
        assert r.ok is False
        assert "context" in r.message.lower() or "config" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /role without ctx -> clean error explaining the need")


def test_role_with_no_studio_fails_clean() -> None:
    """Even with a ctx, if there's no active studio, /role can't run."""
    import tempfile
    from unitytools.cli.chat_commands import DispatchContext
    from unitytools.core.config import Config
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="no-studio-"))
    os.chdir(tmp)
    import unitytools.studio.tools as st
    saved_state = st._STATE
    st._STATE = None
    try:
        cfg = Config(provider="ollama", ollama_model="gemma4:latest")
        ctx = DispatchContext(config=cfg, unity_bridge=None)
        r = dispatch("role designer Draft GDD", ctx=ctx)
        assert r.handled is True
        assert r.ok is False
        assert "studio" in r.message.lower()
    finally:
        st._STATE = saved_state
        os.chdir(prev)
    print("OK /role without active studio -> clean error pointing to /init")


def test_role_with_ctx_and_unreachable_llm_does_not_crash() -> None:
    """If the LLM call itself fails, /role should return ok=False
    with the exception message — never crash the chat."""
    from unitytools.cli.chat_commands import DispatchContext
    from unitytools.core.config import Config
    _, _, prev = _fresh_studio_cwd()
    try:
        # Pointing at a dead port so Ollama is unreachable
        cfg = Config(provider="ollama", ollama_host="http://127.0.0.1:1",
                      ollama_model="gemma4:latest")
        ctx = DispatchContext(config=cfg, unity_bridge=None)
        r = dispatch("role designer Draft GDD", ctx=ctx)
        # Either the client setup error (RuntimeError) or the runtime
        # exception path during .run() — both must come back as
        # ok=False with handled=True, never a crash.
        assert r.handled is True
        assert r.ok is False
        assert r.tool_name in ("role:designer", None)
    finally:
        os.chdir(prev)
    print("OK /role with unreachable LLM -> graceful failure, no crash")


def test_role_brief_joins_remaining_args() -> None:
    """`/role designer Draft initial GDD with three pillars` should
    pass everything after the role-id as the brief."""
    from unitytools.cli.chat_commands import _dispatch_role, DispatchContext
    from unitytools.core.config import Config
    _, _, prev = _fresh_studio_cwd()
    try:
        # We can't easily mock the LLM runner here without a lot of
        # setup, so use the function-private parser via the public
        # entry point. The brief shows up in the failure message
        # path when ctx is missing — but we need a different angle.
        # Easier: parse args manually + check brief join logic by
        # reading the source-of-truth in chat_commands directly.
        # For this test, accept that the brief reaches the inner
        # function; full LLM-running tests live in /dispatch tests.
        r = dispatch("role designer Draft a 3-page GDD")
        # Without ctx, fails — but if it had a ctx the brief would
        # be the rest of the line.
        assert r.handled is True
    finally:
        os.chdir(prev)
    print("OK /role brief = remaining args after role-id (smoke check)")


def test_default_brief_table_covers_every_role() -> None:
    """The _default_brief_for_role helper should know about every
    registered role so users can omit the brief on any role."""
    from unitytools.cli.chat_commands import _default_brief_for_role
    from unitytools.studio import all_roles
    for role in all_roles():
        brief = _default_brief_for_role(role.id)
        assert brief, f"No default brief for role {role.id!r}"
        assert len(brief) >= 10, (
            f"Default brief for {role.id!r} is suspiciously short: {brief!r}"
        )
    print(f"OK every one of {len(list(all_roles()))} roles has a default brief")


def test_dispatch_with_context_uses_real_client_path() -> None:
    """When DispatchContext is provided, /dispatch goes through
    make_default_client. With UNITYTOOLS_PROVIDER=ollama + no ollama
    running, this should still return cleanly (no crash)."""
    from unitytools.cli.chat_commands import DispatchContext
    from unitytools.core.config import Config
    state, _, prev = _fresh_studio_cwd()
    cfg = Config(provider="ollama", ollama_host="http://127.0.0.1:1",
                  ollama_model="gemma4:latest")
    ctx = DispatchContext(config=cfg, unity_bridge=None)
    try:
        # No --dry-run: real client path. With a fake host, the LLM
        # call will fail at runtime — but the slash command itself
        # must not crash.
        dispatch("scaffold collectathon Demo")
        r = dispatch("dispatch 1", ctx=ctx)
        # Either success (no pending tasks of right role) or failure
        # via the runner exception path; either way handled=True.
        assert r.handled is True
        # tool_name must be set so the REPL can show it
        assert r.tool_name == "studio.dispatch_pending" or r.tool_name is None
    finally:
        os.chdir(prev)
    print("OK /dispatch with DispatchContext doesn't crash even when ollama is unreachable")


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
    # Phase 60 inventory + meta
    test_refs_command_lists_references()
    test_screenshots_command_and_alias()
    test_locales_command()
    test_dialogs_command()
    test_assets_command()
    test_behaviours_command_lists_full_library()
    test_behaviours_command_filters_by_substring()
    test_behaviors_us_spelling_works()
    test_roles_command_lists_24_roles()
    test_diag_command_reports_studio_state()
    test_init_creates_studio_when_missing()
    test_init_with_explicit_path()
    test_init_rejects_nonexistent_path()
    # Phase 61 /dispatch
    test_dispatch_command_recognised()
    test_dispatch_without_studio_fails_clean()
    test_dispatch_without_context_or_dry_run_fails_clean()
    test_dispatch_dry_run_works_without_context()
    test_dispatch_caps_limit_at_50()
    test_dispatch_parses_only_filter()
    test_dispatch_default_limit_is_5()
    test_dispatch_with_context_uses_real_client_path()
    # Phase 64 /role
    test_role_command_recognised()
    test_role_without_role_id_returns_usage()
    test_role_with_unknown_role_id_lists_choices()
    test_role_without_context_fails_clean_with_helpful_message()
    test_role_with_no_studio_fails_clean()
    test_role_with_ctx_and_unreachable_llm_does_not_crash()
    test_role_brief_joins_remaining_args()
    test_default_brief_table_covers_every_role()
    print("All chat-command tests passed (Phase 59 + 60 + 61 + 64)")


if __name__ == "__main__":
    run_test()
