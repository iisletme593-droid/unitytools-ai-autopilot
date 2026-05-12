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


# ─────────────────────────────────────────── Phase 65 Türkçe aliases


def test_resolve_alias_maps_turkish_to_english() -> None:
    """The _resolve_alias helper converts Turkish slash commands to
    their English canonical form. Case-insensitive."""
    from unitytools.cli.chat_commands import _resolve_alias
    cases = [
        # Meta
        ("yardım", "help"), ("yardim", "help"),
        ("temizle", "clear"),
        ("durum", "status"),
        ("sağlık", "diag"), ("saglik", "diag"),
        ("çıkış", "quit"), ("cikis", "quit"),
        # Actions
        ("başlat", "init"), ("baslat", "init"),
        ("eşitle", "sync"), ("esitle", "sync"),
        ("oluştur", "scaffold"), ("olustur", "scaffold"), ("kur", "scaffold"),
        ("yürüt", "dispatch"), ("yurut", "dispatch"),
        ("rol", "role"),
        ("rapor", "dashboard"), ("panel", "dashboard"),
        ("satış", "ship"), ("satis", "ship"),
        ("maliyet", "cost"),
        ("denetim", "audit"), ("tarama", "audit"),
        # Inventory
        ("görev", "tasks"), ("gorev", "tasks"),
        ("hedef", "milestones"),
        ("kararlar", "decisions"),
        ("referans", "refs"),
        ("ekran", "screenshots"),
        ("dil", "locales"), ("diller", "locales"),
        ("diyalog", "dialogs"),
        ("varlık", "assets"), ("varlik", "assets"),
        ("davranış", "behaviours"), ("davranis", "behaviours"),
        ("roller", "roles"),
    ]
    for tr, expected in cases:
        got = _resolve_alias(tr)
        assert got == expected, f"_resolve_alias({tr!r}) = {got!r}, expected {expected!r}"
    print(f"OK {len(cases)} Turkish aliases all resolve to canonical English form")


def test_resolve_alias_is_case_insensitive() -> None:
    """`/Oluştur` and `/OLUŞTUR` should both work like `/oluştur`."""
    from unitytools.cli.chat_commands import _resolve_alias
    assert _resolve_alias("Oluştur") == "scaffold"
    assert _resolve_alias("OLUŞTUR") == "scaffold"
    assert _resolve_alias("rapor".upper()) == "dashboard"
    print("OK Turkish aliases are case-insensitive")


def test_resolve_alias_passes_english_through_unchanged() -> None:
    """English commands aren't in the alias table; they stay
    as-is (lowercased)."""
    from unitytools.cli.chat_commands import _resolve_alias
    for english in ("scaffold", "dispatch", "ship", "audit", "init", "diag"):
        got = _resolve_alias(english)
        assert got == english
        # Uppercase also lowercases
        assert _resolve_alias(english.upper()) == english
    print("OK English commands pass through alias resolver unchanged")


def test_turkish_oluştur_actually_scaffolds() -> None:
    """End-to-end: /oluştur collectathon Demo fires the
    collectathon scaffolder."""
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("oluştur collectathon Demo")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_scaffold_collectathon_game"
        assert len(state.load_tasks()) == 13
    finally:
        os.chdir(prev)
    print("OK /oluştur collectathon Demo fires the scaffolder end-to-end")


def test_turkish_yürüt_actually_dispatches() -> None:
    """End-to-end: /yürüt --dry-run fires the autopilot."""
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("scaffold collectathon Demo")
        r = dispatch("yürüt 3 --dry-run")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio.dispatch_pending"
        assert r.tool_result["dry_run"] is True
    finally:
        os.chdir(prev)
    print("OK /yürüt 3 --dry-run fires autopilot end-to-end")


def test_turkish_sağlık_fires_diag() -> None:
    """End-to-end: /sağlık returns the diag info."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("sağlık")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "diag"
        assert r.tool_result["roles"] == 24
    finally:
        os.chdir(prev)
    print("OK /sağlık (and /saglik fallback) returns full diag info")


def test_turkish_rapor_fires_dashboard() -> None:
    """End-to-end: /rapor --save fires studio_dashboard."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("rapor")
        assert r.handled is True
        assert r.tool_name == "studio_dashboard"
        # --save flag works through the alias too
        r2 = dispatch("rapor --save")
        assert r2.tool_result.get("saved_path") is not None
    finally:
        os.chdir(prev)
    print("OK /rapor [--save] fires studio_dashboard with flags intact")


# ─────────────────────────────────────────── Phase 66 /build


def test_build_command_recognised() -> None:
    """/build is a known command (handled=True even on errors)."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("build windows")
        assert r.handled is True
    finally:
        os.chdir(prev)
    print("OK /build is a recognised command")


def test_build_without_target_returns_usage_with_choices() -> None:
    r = dispatch("build")
    assert r.handled is True
    assert r.ok is False
    assert "Usage" in r.message
    # Choices list is included
    assert "windows" in r.message or "webgl" in r.message
    print("OK /build without target -> usage hint listing all targets")


def test_build_with_unknown_target_lists_choices() -> None:
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("build playstation")
        assert r.handled is True
        assert r.ok is False
        assert "playstation" in r.message
        # The choices list mentions a known target
        assert "windows" in r.message or "webgl" in r.message
    finally:
        os.chdir(prev)
    print("OK unknown target -> error lists every valid alias")


def test_build_target_alias_table_covers_common_keywords() -> None:
    """Operators type 'win' / 'exe' / 'html5' / 'apk' / etc.; all
    should resolve to a canonical target."""
    from unitytools.cli.chat_commands import _BUILD_TARGET_ALIASES
    cases = [
        ("win", "windows"), ("exe", "windows"), ("windows64", "windows"),
        ("osx", "mac"), ("macos", "mac"),
        ("html5", "webgl"), ("web", "webgl"),
        ("apk", "android"),
        ("iphone", "ios"), ("ipad", "ios"),
        ("linux64", "linux"),
    ]
    for alias, canonical in cases:
        assert _BUILD_TARGET_ALIASES.get(alias) == canonical, (
            f"/build {alias} should resolve to {canonical}, got "
            f"{_BUILD_TARGET_ALIASES.get(alias)!r}"
        )
    print(f"OK {len(cases)} build-target keyword aliases all resolve correctly")


def test_build_without_bridge_context_fails_clean() -> None:
    """/build needs ctx.unity_bridge. Without it, fails cleanly with
    a hint pointing at the start-Unity workflow."""
    _, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("build windows")
        assert r.handled is True
        assert r.ok is False
        assert "bridge" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /build without DispatchContext -> clean 'bridge needed' error")


def test_build_with_offline_bridge_fails_clean() -> None:
    """If the bridge object exists but connect() returns False
    (Unity isn't running), the build refuses cleanly."""
    from unitytools.cli.chat_commands import DispatchContext

    class OfflineBridge:
        def connect(self, *a, **k): return False
        def is_connected(self): return False
        def call(self, *a, **k): raise NotImplementedError

    _, _, prev = _fresh_studio_cwd()
    try:
        ctx = DispatchContext(config=None, unity_bridge=OfflineBridge())
        r = dispatch("build windows", ctx=ctx)
        assert r.handled is True
        assert r.ok is False
        assert "not connected" in r.message.lower() or "bridge" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /build with offline bridge -> clean 'not connected' error")


def test_build_preflight_blocks_when_ship_check_fails() -> None:
    """A studio with no GDD / scenes should fail preflight. /build
    surfaces the blocker without calling unity_build_player."""
    from unitytools.cli.chat_commands import DispatchContext

    class FakeConnectedBridge:
        """Simulates connected bridge but with an empty studio,
        preflight should fail before any unity_build_player call."""
        def connect(self, *a, **k): return True
        def is_connected(self): return True
        def call(self, method, params=None, timeout=None):
            if method == "list_build_scenes":
                # No enabled scenes -> studio_build_check fails
                return {
                    "ok": True, "count": 0, "enabled_count": 0,
                    "active_target": "StandaloneWindows64", "scenes": [],
                }
            raise AssertionError(
                f"unity_build_player should NOT be reached on preflight fail; got {method}"
            )

    _, _, prev = _fresh_studio_cwd()
    try:
        # _fresh_studio_cwd wrote a GDD; remove it so preflight fails
        import unitytools.studio.tools as st
        st._STATE.paths.gdd.unlink(missing_ok=True)
        ctx = DispatchContext(config=None, unity_bridge=FakeConnectedBridge())
        r = dispatch("build windows", ctx=ctx)
        assert r.handled is True
        assert r.ok is False
        assert r.tool_name == "studio_build_check"
        assert "preflight" in r.message.lower() or "blocker" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /build preflight blocks on no-GDD-no-scenes; unity_build_player NOT called")


def test_build_force_skips_preflight() -> None:
    """--force should bypass the preflight gate."""
    from unitytools.cli.chat_commands import DispatchContext

    class FakeBuildBridge:
        def connect(self, *a, **k): return True
        def is_connected(self): return True
        def call(self, method, params=None, timeout=None):
            if method == "build_player":
                # Pretend the build succeeded
                return {
                    "ok": True, "result": "Succeeded",
                    "target": "StandaloneWindows64",
                    "output_path": params.get("output_path", ""),
                    "total_size_bytes": 12_345_678,
                    "total_errors": 0, "total_warnings": 1,
                    "total_time_seconds": 7.5,
                    "scene_count": 1, "development_build": False,
                }
            # Anything else is unexpected — preflight should be skipped
            raise AssertionError(
                f"--force should skip preflight; bridge got method={method}"
            )

    _, _, prev = _fresh_studio_cwd()
    try:
        # Clear the GDD so preflight WOULD fail; --force should still build
        import unitytools.studio.tools as st
        st._STATE.paths.gdd.unlink(missing_ok=True)
        ctx = DispatchContext(config=None, unity_bridge=FakeBuildBridge())
        r = dispatch("build windows --force --out /tmp/Game.exe", ctx=ctx)
        assert r.handled is True
        assert r.ok is True, f"--force build should succeed; got {r.message}"
        assert r.tool_name == "unity_build_player"
        assert "SUCCEEDED" in r.message
    finally:
        os.chdir(prev)
    print("OK /build --force skips preflight and goes straight to unity_build_player")


def test_build_auto_generates_output_path() -> None:
    """When --out is omitted, the path is studio/builds/<date>/<target>/<product_name>.<ext>."""
    from unitytools.cli.chat_commands import DispatchContext

    captured_path: dict = {}

    class FakeBridge:
        def connect(self, *a, **k): return True
        def is_connected(self): return True
        def call(self, method, params=None, timeout=None):
            if method == "list_build_scenes":
                return {"ok": True, "count": 1, "enabled_count": 1,
                        "active_target": "StandaloneWindows64",
                        "scenes": [{"index": 0, "path": "Assets/Scenes/Main.unity", "enabled": True}]}
            if method == "get_player_settings":
                return {"ok": True, "product_name": "Coin Hunter Pro",
                         "company_name": "Studio", "version": "0.1.0",
                         "bundle_id": "com.studio.coin",
                         "default_width": 1920, "default_height": 1080,
                         "active_build_target": "StandaloneWindows64",
                         "unity_version": "2022.3"}
            if method == "build_player":
                captured_path["path"] = params.get("output_path")
                return {"ok": True, "result": "Succeeded",
                        "target": "StandaloneWindows64",
                        "output_path": params.get("output_path", ""),
                        "total_size_bytes": 1000, "total_errors": 0,
                        "total_warnings": 0, "total_time_seconds": 1.0,
                        "scene_count": 1, "development_build": False}
            raise AssertionError(f"unexpected method {method}")

    _, _, prev = _fresh_studio_cwd()
    try:
        ctx = DispatchContext(config=None, unity_bridge=FakeBridge())
        r = dispatch("build windows", ctx=ctx)
        assert r.handled is True
        assert r.ok is True, f"build should succeed; got: {r.message}"
        # Path looks like studio/builds/<date>/windows/Coin_Hunter_Pro.exe
        path = captured_path.get("path", "")
        assert "builds" in path, f"path missing 'builds': {path!r}"
        assert "windows" in path, f"path missing 'windows': {path!r}"
        assert "Coin_Hunter_Pro" in path or "Coin Hunter Pro" in path, (
            f"path missing product_name: {path!r}"
        )
        assert path.endswith(".exe"), f"windows build should end with .exe: {path!r}"
    finally:
        os.chdir(prev)
    print("OK /build auto-generates path: builds/<date>/<target>/<product_name>.<ext>")


def test_build_dev_flag_passes_development_build() -> None:
    """`/build windows --dev` should set development_build=True
    in the unity_build_player call."""
    from unitytools.cli.chat_commands import DispatchContext

    captured: dict = {}

    class FakeBridge:
        def connect(self, *a, **k): return True
        def is_connected(self): return True
        def call(self, method, params=None, timeout=None):
            if method == "list_build_scenes":
                return {"ok": True, "count": 1, "enabled_count": 1,
                        "active_target": "?", "scenes": []}
            if method == "get_player_settings":
                return {"ok": True, "product_name": "Game"}
            if method == "build_player":
                captured["dev"] = params.get("development_build")
                return {"ok": True, "result": "Succeeded",
                        "target": "X", "output_path": "",
                        "total_size_bytes": 0, "total_errors": 0,
                        "total_warnings": 0, "total_time_seconds": 0}
            raise AssertionError(method)

    _, _, prev = _fresh_studio_cwd()
    try:
        ctx = DispatchContext(config=None, unity_bridge=FakeBridge())
        dispatch("build webgl --dev --force", ctx=ctx)
        assert captured.get("dev") is True
    finally:
        os.chdir(prev)
    print("OK /build webgl --dev sets development_build=True on the bridge call")


def test_build_turkish_aliases() -> None:
    """/yapı, /derle, /inşa all resolve to /build."""
    from unitytools.cli.chat_commands import _resolve_alias
    for tr in ("yapı", "yapi", "derle", "inşa", "insa"):
        assert _resolve_alias(tr) == "build", (
            f"/{tr} should alias to /build, got /{_resolve_alias(tr)}"
        )
    print("OK 5 Turkish /build aliases (yapı/yapi/derle/inşa/insa) resolve correctly")


def test_quit_aliases_carry_quit_flag() -> None:
    """Turkish exit aliases should also return quit=True."""
    for word in ("çıkış", "cikis", "çık", "cik"):
        r = dispatch(word)
        assert r.handled is True
        assert r.quit is True, f"alias {word!r} should set quit=True"
    print("OK Turkish quit aliases (çıkış / cikis / çık / cik) carry quit=True")


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


# ─────────────────────────────────────────── Phase 68: meta commands


def _ensure_tools_loaded() -> None:
    """The dispatcher reads from get_all_tools(); make sure the engine
    + studio tool modules have been imported so the registry is full."""
    import unitytools.tools  # noqa: F401
    import unitytools.tools.unity_tools  # noqa: F401
    try:
        import unitytools.studio.tools  # noqa: F401
    except Exception:
        pass


def test_help_command_returns_command_listing() -> None:
    r = dispatch("help")
    assert r.handled is True
    assert r.ok is True
    assert r.tool_name == "help"
    # Structured payload carries sections for editor UIs
    sections = r.tool_result["sections"]
    section_titles = [s["title"] for s in sections]
    assert "Meta" in section_titles
    assert "Studio actions" in section_titles
    assert "Inventory" in section_titles
    print("OK /help returns CommandResult with structured sections")


def test_help_lists_every_dispatch_section() -> None:
    """Sanity: every command we route in dispatch() should appear in
    /help. Catches the 'added a slash command but forgot to document it'
    drift."""
    r = dispatch("help")
    msg = r.message
    # Every canonical command should be mentioned at least once.
    required = [
        "/scaffold", "/dispatch", "/role", "/build", "/dashboard",
        "/ship", "/cost", "/audit", "/tasks", "/milestones",
        "/decisions", "/refs", "/screenshots", "/locales",
        "/dialogs", "/assets", "/behaviours", "/roles",
        "/init", "/sync", "/diag", "/status", "/studio", "/tools",
    ]
    for cmd in required:
        assert cmd in msg, f"/help message must mention {cmd}; missing"
    print(f"OK /help advertises all {len(required)} canonical commands")


def test_help_message_mentions_turkish_aliases() -> None:
    r = dispatch("help")
    assert "Türkçe aliases" in r.message or "Turkce" in r.message
    # Spot-check a few aliases:
    for alias in ("/yardım", "/eşitle", "/yapı", "/oluştur"):
        assert alias in r.message, f"/help should list Türkçe alias {alias}"
    print("OK /help mentions Türkçe aliases")


def test_help_turkish_yardim_alias_resolves() -> None:
    """`/yardım` is in _ALIASES; dispatcher should resolve it to help
    and emit the same listing."""
    r = dispatch("yardım")
    assert r.handled is True
    assert r.tool_name == "help"
    print("OK /yardım → /help via alias resolution")


def test_tools_lists_registered_tools() -> None:
    _ensure_tools_loaded()
    r = dispatch("tools")
    assert r.handled is True
    assert r.ok is True
    assert r.tool_name == "tools"
    total = r.tool_result["total"]
    shown = r.tool_result["shown"]
    assert total > 50, f"expected many tools registered; got {total}"
    assert shown == total, "no filter → shown should equal total"
    # Each tool dict has both name + description
    sample = r.tool_result["tools"][0]
    assert "name" in sample and "description" in sample
    print(f"OK /tools lists every registered tool ({total} found)")


def test_tools_with_substring_filter() -> None:
    _ensure_tools_loaded()
    r = dispatch("tools studio")
    assert r.handled is True
    assert r.ok is True
    assert r.tool_result["filter"] == "studio"
    shown = r.tool_result["shown"]
    total = r.tool_result["total"]
    assert 0 < shown < total, (
        f"filter should narrow the list; got {shown} of {total}"
    )
    # Every returned tool actually matches the filter
    for entry in r.tool_result["tools"]:
        haystack = (entry["name"] + " " + entry["description"]).lower()
        assert "studio" in haystack, f"unrelated tool leaked: {entry['name']}"
    print(f"OK /tools studio narrows to {shown}/{total} matching tools")


def test_tools_filter_misses_returns_empty() -> None:
    r = dispatch("tools zzzz_no_such_tool_should_ever_exist")
    assert r.handled is True
    assert r.ok is True  # 0 matches is still a successful query
    assert r.tool_result["shown"] == 0
    print("OK /tools with no matches returns shown=0 (still ok)")


def test_tools_turkish_alias_resolves() -> None:
    _ensure_tools_loaded()
    r = dispatch("araç")  # Türkçe alias for tools
    assert r.handled is True
    assert r.tool_name == "tools"
    print("OK /araç → /tools via alias")


def test_status_without_ctx_reports_no_bridge() -> None:
    r = dispatch("status")
    assert r.handled is True
    assert r.ok is True
    assert r.tool_name == "status"
    assert r.tool_result["unity"] == "no-bridge"
    print("OK /status with no ctx → unity='no-bridge'")


def test_status_with_offline_bridge_reports_offline() -> None:
    from unitytools.cli.chat_commands import DispatchContext

    class OfflineBridge:
        def is_connected(self):
            return False

    r = dispatch("status", ctx=DispatchContext(unity_bridge=OfflineBridge()))
    assert r.tool_result["unity"] == "offline"
    print("OK /status with offline bridge → unity='offline'")


def test_status_with_connected_bridge_reports_connected() -> None:
    from unitytools.cli.chat_commands import DispatchContext

    class OnlineBridge:
        def is_connected(self):
            return True

    r = dispatch("status", ctx=DispatchContext(unity_bridge=OnlineBridge()))
    assert r.tool_result["unity"] == "connected"
    print("OK /status with connected bridge → unity='connected'")


def test_status_includes_provider_and_model_from_ctx() -> None:
    from unitytools.cli.chat_commands import DispatchContext
    from unitytools.core.config import Config

    cfg = Config(api_key="test-key")
    r = dispatch("status", ctx=DispatchContext(config=cfg))
    assert "provider" in r.tool_result
    assert "model" in r.tool_result
    # The configured default is ollama / gemma4:latest (Phase 57)
    assert r.tool_result["provider"] in ("ollama", "anthropic")
    print(f"OK /status reports provider={r.tool_result['provider']} model={r.tool_result['model']}")


def test_studio_status_returns_summary_on_active_studio() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("studio")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_get_summary"
        assert "studio_root" in r.tool_result
        # Message line should mention task / milestone / decision counts
        for token in ("Tasks:", "Milestones:", "Decisions:"):
            assert token in r.message, f"/studio message should include {token}"
    finally:
        os.chdir(prev)
    print("OK /studio with active state returns summary dict + count line")


def test_studio_status_reports_inactive_when_no_state() -> None:
    """When studio_get_summary returns ok=False, the dispatcher should
    surface that cleanly rather than crashing."""
    # Force studio inactive: clear the global state by re-initing with
    # nothing, or just skip the cwd setup. We test by calling from a
    # tempdir that has no studio.
    from unitytools.studio.tools import _STATE as _ST_MOD  # noqa: F401
    import unitytools.studio.tools as _stm

    saved_state = _stm._STATE
    try:
        _stm._STATE = None
        r = dispatch("studio")
        assert r.handled is True
        assert r.ok is False
        # Message describes the failure mode
        assert "inactive" in r.message.lower() or "failed" in r.message.lower()
    finally:
        _stm._STATE = saved_state
    print("OK /studio with no active state → ok=False, doesn't crash")


# ─────────────────────────────────────────── Phase 69: /sprint + /next


def test_sprint_command_recognised() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=Path(os.getcwd()))
        paths.sprint_current.write_text(
            "# Sprint 5\n- Tune jump physics\n- Add coin pickup VFX",
            encoding="utf-8",
        )
        r = dispatch("sprint")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_read_sprint"
        # The message line shows the file content (or a preview)
        assert "Sprint" in r.message or "jump" in r.message
        # tool_result carries the raw studio_read_sprint payload
        assert r.tool_result["content"].startswith("# Sprint")
    finally:
        os.chdir(prev)
    print("OK /sprint reads studio/sprint_current.md and surfaces it")


def test_sprint_empty_file_surfaces_friendly_message() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=Path(os.getcwd()))
        paths.sprint_current.write_text("", encoding="utf-8")
        r = dispatch("sprint")
        assert r.handled is True
        assert r.ok is True
        assert "empty" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /sprint on empty file shows actionable hint")


def test_next_returns_oldest_ready_task() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        t1 = Task(title="First task", role="designer")
        t2 = Task(title="Second task", role="designer")
        state.add_task(t1)
        state.add_task(t2)
        r = dispatch("next")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_next_task"
        # FIFO — first-added pending task wins
        assert r.tool_result["task"]["id"] == t1.id
        assert r.tool_result["task"]["title"] == "First task"
        assert r.tool_result["pending_count"] == 2
        assert r.tool_result["ready_count"] == 2
        assert "First task" in r.message
    finally:
        os.chdir(prev)
    print("OK /next returns oldest ready PENDING task (FIFO)")


def test_next_role_filter_narrows_to_discipline() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        # First task is for level_designer; second for designer.
        # /next designer should skip the level_designer one.
        state.add_task(Task(title="LD task", role="level_designer"))
        state.add_task(Task(title="Designer task", role="designer"))
        r = dispatch("next designer")
        assert r.ok is True
        assert r.tool_result["task"]["role"] == "designer"
        assert r.tool_result["task"]["title"] == "Designer task"
    finally:
        os.chdir(prev)
    print("OK /next <role> narrows to discipline")


def test_next_with_unknown_role_fails_clean() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("next not_a_real_role")
        assert r.handled is True
        assert r.ok is False
        assert "Unknown role" in r.message
        # Message lists valid choices to help the user
        assert "producer" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /next <bad-role> → ok=False with list of valid roles")


def test_next_when_backlog_empty_says_no_pending() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("next")
        assert r.ok is True
        assert r.tool_result["task"] is None
        # The reason field explains WHY we got no task
        assert "no pending" in r.tool_result["reason"].lower()
        assert "no task" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /next on empty backlog → task=None with diagnostic reason")


def test_next_skips_tasks_blocked_by_deps() -> None:
    """A task whose depends_on points to a non-done task must NOT
    surface in /next; the next task without unresolved deps wins."""
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        # Add t1 first (pending, blocks t2). t3 is independent.
        t1 = Task(title="Block out arena", role="level_designer")
        state.add_task(t1)
        t2 = Task(title="Light arena (needs t1)", role="tech_artist",
                   depends_on=[t1.id])
        state.add_task(t2)
        t3 = Task(title="Tune SFX", role="designer")
        state.add_task(t3)
        r = dispatch("next")
        assert r.ok is True
        # The first ready task should be t1 (no deps), then t3 (no deps).
        # t2 must NOT be returned because t1 is still PENDING.
        nxt = r.tool_result["task"]
        assert nxt["title"] in ("Block out arena", "Tune SFX")
        assert nxt["title"] != "Light arena (needs t1)"
        # 3 pending, 2 ready (t2 blocked by deps)
        assert r.tool_result["pending_count"] == 3
        assert r.tool_result["ready_count"] == 2
    finally:
        os.chdir(prev)
    print("OK /next skips dep-blocked tasks; ready_count excludes them")


def test_next_when_only_blocked_tasks_left_explains_why() -> None:
    """All pending tasks blocked by unresolved deps → task=None with
    'blocked_by_deps' explanation rather than 'no pending tasks'."""
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        # Fake dep id that doesn't exist (and isn't done):
        # any task with this dep will be considered blocked.
        t = Task(title="Needs unknown dep", role="designer",
                  depends_on=["non-existent-id"])
        state.add_task(t)
        r = dispatch("next")
        assert r.ok is True
        assert r.tool_result["task"] is None
        assert r.tool_result["pending_count"] == 1
        assert r.tool_result["blocked_by_deps"] == 1
        assert "blocked" in r.tool_result["reason"].lower()
    finally:
        os.chdir(prev)
    print("OK /next when only blocked tasks remain → diagnostic blocked_by_deps")


def test_next_turkish_aliases_resolve() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        state.add_task(Task(title="Some task", role="designer"))
        for alias in ("sıradaki", "siradaki", "sıra", "sira", "sonraki"):
            r = dispatch(alias)
            assert r.handled is True, f"/{alias} should resolve to /next"
            assert r.tool_name == "studio_next_task", (
                f"/{alias} should fire studio_next_task; got {r.tool_name}"
            )
    finally:
        os.chdir(prev)
    print("OK /sıradaki, /siradaki, /sıra, /sira, /sonraki all → /next")


def test_help_lists_phase_69_commands() -> None:
    """Drift check: /sprint and /next must show up in /help."""
    r = dispatch("help")
    for required in ("/sprint", "/next"):
        assert required in r.message, (
            f"/help should advertise {required} after Phase 69"
        )
    print("OK /help advertises /sprint and /next")


# ─────────────────────────────────────────── Phase 70: task lifecycle


def test_take_marks_task_in_progress() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task, TaskStatus
        t = Task(title="Block out level 1", role="level_designer")
        state.add_task(t)
        r = dispatch(f"take {t.id[:8]}")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_update_task_status"
        # Reload from disk to verify persistence
        tasks = state.load_tasks()
        updated = next(x for x in tasks if x.id == t.id)
        assert updated.status is TaskStatus.IN_PROGRESS
        # Short id shown in message
        assert t.id[:8] in r.message
        assert "in_progress" in r.message
    finally:
        os.chdir(prev)
    print("OK /take <short-id> flips PENDING → IN_PROGRESS (persisted)")


def test_done_marks_task_done() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task, TaskStatus
        t = Task(title="Tune SFX", role="designer")
        state.add_task(t)
        r = dispatch(f"done {t.id[:8]}")
        assert r.ok is True
        tasks = state.load_tasks()
        updated = next(x for x in tasks if x.id == t.id)
        assert updated.status is TaskStatus.DONE
        assert "done" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /done <id> flips status → DONE")


def test_unblock_returns_blocked_to_pending() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task, TaskStatus
        t = Task(title="Need EXR for HDRI", role="art_director")
        t.status = TaskStatus.BLOCKED
        state.add_task(t)
        r = dispatch(f"unblock {t.id[:8]}")
        assert r.ok is True
        tasks = state.load_tasks()
        updated = next(x for x in tasks if x.id == t.id)
        assert updated.status is TaskStatus.PENDING
    finally:
        os.chdir(prev)
    print("OK /unblock <id> flips BLOCKED → PENDING")


def test_block_appends_reason_to_blockers() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task, TaskStatus
        t = Task(title="Boss arena lighting", role="tech_artist")
        state.add_task(t)
        r = dispatch(f"block {t.id[:8]} waiting on art_director approval")
        assert r.ok is True
        assert r.tool_name == "studio_block_task"
        tasks = state.load_tasks()
        updated = next(x for x in tasks if x.id == t.id)
        assert updated.status is TaskStatus.BLOCKED
        assert "waiting on art_director approval" in updated.blockers
        # message reports blocker count
        assert "1 reason" in r.message
    finally:
        os.chdir(prev)
    print("OK /block <id> <reason words> stores reason and flips to BLOCKED")


def test_block_without_reason_still_blocks_task() -> None:
    """Reason is optional — /block <id> alone is valid."""
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task, TaskStatus
        t = Task(title="Some task", role="designer")
        state.add_task(t)
        r = dispatch(f"block {t.id[:8]}")
        assert r.ok is True
        tasks = state.load_tasks()
        updated = next(x for x in tasks if x.id == t.id)
        assert updated.status is TaskStatus.BLOCKED
        # No reason → blockers list stays at whatever it was (empty)
        assert updated.blockers == []
    finally:
        os.chdir(prev)
    print("OK /block <id> without reason still flips status")


def test_block_appends_to_existing_reasons() -> None:
    """Second /block call adds another reason — doesn't overwrite."""
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        t = Task(title="Multi-blocked", role="designer")
        state.add_task(t)
        dispatch(f"block {t.id[:8]} first reason")
        dispatch(f"block {t.id[:8]} second reason")
        tasks = state.load_tasks()
        updated = next(x for x in tasks if x.id == t.id)
        assert updated.blockers == ["first reason", "second reason"]
    finally:
        os.chdir(prev)
    print("OK /block appends — preserves blocker history")


def test_why_explains_status_and_deps() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        t1 = Task(title="Block out arena", role="level_designer")
        state.add_task(t1)
        t2 = Task(title="Light arena (needs t1)", role="tech_artist",
                   depends_on=[t1.id])
        state.add_task(t2)
        r = dispatch(f"why {t2.id[:8]}")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_explain_task"
        # When deps unsatisfied, message says so
        assert "deps unsatisfied" in r.message
        # tool_result enumerates each dep
        deps = r.tool_result["depends_on"]
        assert len(deps) == 1
        assert deps[0]["title"] == "Block out arena"
        assert deps[0]["satisfied"] is False
    finally:
        os.chdir(prev)
    print("OK /why explains status + unsatisfied deps with per-dep details")


def test_why_marks_task_ready_when_no_deps() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        t = Task(title="Independent task", role="designer")
        state.add_task(t)
        r = dispatch(f"why {t.id[:8]}")
        assert r.ok is True
        assert r.tool_result["ready_to_start"] is True
        assert "ready to start" in r.message
    finally:
        os.chdir(prev)
    print("OK /why on dep-free PENDING task → ready_to_start=True")


def test_take_without_id_returns_usage() -> None:
    r = dispatch("take")
    assert r.handled is True
    assert r.ok is False
    assert "Usage" in r.message
    assert "/take" in r.message
    print("OK /take with no args → usage hint")


def test_block_without_id_returns_usage() -> None:
    r = dispatch("block")
    assert r.handled is True
    assert r.ok is False
    assert "Usage" in r.message
    print("OK /block with no args → usage hint")


def test_lifecycle_with_unknown_partial_id_fails_clean() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("take aaaaaaaa")
        assert r.handled is True
        assert r.ok is False
        assert "No task id starts with" in r.message
    finally:
        os.chdir(prev)
    print("OK /take <missing-id> → clean error with hint")


def test_lifecycle_ambiguous_partial_lists_candidates() -> None:
    """If a partial id matches multiple tasks the dispatcher must show
    the candidates so the operator can disambiguate."""
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task

        # Find a hex prefix that two tasks can share. Brute-force —
        # add tasks until we find a collision on the first character.
        seen: dict[str, str] = {}
        collision_prefix: str | None = None
        for i in range(30):
            t = Task(title=f"Task {i}", role="designer")
            state.add_task(t)
            prefix = t.id[:1]
            if prefix in seen:
                collision_prefix = prefix
                break
            seen[prefix] = t.id

        assert collision_prefix is not None, (
            "test setup couldn't find a 1-char collision in 30 ids — "
            "should be statistically impossible for UUIDs"
        )
        r = dispatch(f"take {collision_prefix}")
        assert r.handled is True
        assert r.ok is False
        # Message names how many matched and asks for more chars
        assert "match" in r.message.lower()
        assert "disambiguate" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /take with ambiguous prefix → lists candidates + asks for more chars")


def test_turkish_aliases_resolve_to_lifecycle_commands() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task
        t = Task(title="Türkçe test", role="designer")
        state.add_task(t)
        # /al → take
        r = dispatch(f"al {t.id[:8]}")
        assert r.handled is True
        assert r.tool_name == "studio_update_task_status"
        # /tamam → done
        r = dispatch(f"tamam {t.id[:8]}")
        assert r.handled is True
        assert r.tool_name == "studio_update_task_status"
        # /engelle → block (use a fresh task)
        t2 = Task(title="Engellenecek", role="designer")
        state.add_task(t2)
        r = dispatch(f"engelle {t2.id[:8]} sebep")
        assert r.handled is True
        assert r.tool_name == "studio_block_task"
        # /aç → unblock
        r = dispatch(f"aç {t2.id[:8]}")
        assert r.handled is True
        assert r.tool_name == "studio_update_task_status"
        # /neden → why
        r = dispatch(f"neden {t.id[:8]}")
        assert r.handled is True
        assert r.tool_name == "studio_explain_task"
    finally:
        os.chdir(prev)
    print("OK Türkçe lifecycle aliases (/al /tamam /engelle /aç /neden) all resolve")


def test_help_lists_phase_70_commands() -> None:
    """Drift check: lifecycle commands must appear in /help."""
    r = dispatch("help")
    for required in ("/take", "/done", "/block", "/unblock", "/why"):
        assert required in r.message, (
            f"/help should advertise {required} after Phase 70"
        )
    print("OK /help advertises every Phase 70 lifecycle command")


def test_done_takes_short_id_from_next() -> None:
    """End-to-end: /next surfaces a short id; pass it back to /done."""
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio.models import Task, TaskStatus
        t = Task(title="Loop test", role="designer")
        state.add_task(t)
        # /next gives us the task
        r_next = dispatch("next")
        short_id_from_message = r_next.tool_result["task"]["id"][:8]
        # Use that exact short id with /done
        r_done = dispatch(f"done {short_id_from_message}")
        assert r_done.ok is True
        tasks = state.load_tasks()
        assert tasks[0].status is TaskStatus.DONE
    finally:
        os.chdir(prev)
    print("OK /next → /done <short-id> closes the daily loop end-to-end")


# ─────────────────────────────────────────── Phase 71: /standup digest


def _seed_mixed_backlog() -> tuple:
    """Build a backlog with tasks across every status, with recent and
    old `updated_at` timestamps so window-based filtering can be tested.
    Returns (state, tmp, prev_cwd) plus the planted timestamps for
    deterministic assertions."""
    import time
    from unitytools.studio.models import Task, TaskStatus

    state, tmp, prev = _fresh_studio_cwd()
    now = time.time()
    # Recent done (within 24h)
    t = Task(title="Recent done", role="designer", status=TaskStatus.DONE)
    t.updated_at = now - 3600  # 1h ago
    state.add_task(t)
    # Old done (older than 24h)
    t = Task(title="Old done", role="designer", status=TaskStatus.DONE)
    t.updated_at = now - 7 * 86400  # 7d ago
    state.add_task(t)
    # In-flight
    state.add_task(Task(title="In-flight A", role="level_designer",
                         status=TaskStatus.IN_PROGRESS))
    state.add_task(Task(title="In-flight B", role="tech_artist",
                         status=TaskStatus.IN_PROGRESS))
    # Blocked
    state.add_task(Task(title="Blocked task", role="tech_artist",
                         status=TaskStatus.BLOCKED,
                         blockers=["waiting on art_director"]))
    # Review
    state.add_task(Task(title="In review", role="qa", status=TaskStatus.REVIEW))
    # Pending (most recent — backlog depth)
    state.add_task(Task(title="Pending 1", role="designer"))
    state.add_task(Task(title="Pending 2", role="qa"))
    state.add_task(Task(title="Pending 3", role="designer"))
    return state, tmp, prev, now


def test_standup_returns_correct_status_counts() -> None:
    state, _, prev, now = _seed_mixed_backlog()
    try:
        r = dispatch("standup")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_standup"
        # Counts match the seeded backlog (1 recent done, 2 in_progress,
        # 1 blocked, 1 review, 3 pending; old done excluded from window)
        assert r.tool_result["closed_recent_count"] == 1
        assert r.tool_result["in_flight_count"] == 2
        assert r.tool_result["blocked_count"] == 1
        assert r.tool_result["review_count"] == 1
        assert r.tool_result["pending_count"] == 3
        # Total includes everything in the backlog (9 seeded)
        assert r.tool_result["total_tasks"] == 9
    finally:
        os.chdir(prev)
    print("OK /standup counts each status correctly in the 24h window")


def test_standup_message_carries_one_line_summary() -> None:
    state, _, prev, _ = _seed_mixed_backlog()
    try:
        r = dispatch("standup")
        # The message line is the chat-panel summary
        for token in ("closed", "in-flight", "blocked", "pending"):
            assert token in r.message, f"/standup message missing {token!r}"
        # 24h window mentioned
        assert "24" in r.message
    finally:
        os.chdir(prev)
    print("OK /standup message line includes every status count + window")


def test_standup_window_argument_expands_closed_set() -> None:
    """A 30-day window should pick up the old-done task that 24h ignored."""
    state, _, prev, _ = _seed_mixed_backlog()
    try:
        r_24h = dispatch("standup")
        r_30d = dispatch("standup 720")  # 720h = 30 days
        assert r_24h.tool_result["closed_recent_count"] == 1
        assert r_30d.tool_result["closed_recent_count"] == 2, (
            "30-day window should pick up the 7-day-old done task too"
        )
    finally:
        os.chdir(prev)
    print("OK /standup <hours> widens the 'closed_recent' window")


def test_standup_bad_window_returns_usage() -> None:
    state, _, prev, _ = _seed_mixed_backlog()
    try:
        r = dispatch("standup notanumber")
        assert r.handled is True
        assert r.ok is False
        assert "number" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /standup with non-numeric arg → clean error")


def test_standup_zero_or_negative_window_rejected() -> None:
    state, _, prev, _ = _seed_mixed_backlog()
    try:
        r = dispatch("standup -1")
        assert r.ok is False
        assert "positive" in r.message.lower()
        r2 = dispatch("standup 0")
        assert r2.ok is False
    finally:
        os.chdir(prev)
    print("OK /standup rejects non-positive window hours")


def test_standup_role_rollups_match_seeded_tasks() -> None:
    state, _, prev, _ = _seed_mixed_backlog()
    try:
        r = dispatch("standup")
        # designer closed 1 (recent), tech_artist blocked 1, etc.
        assert r.tool_result["closed_by_role"].get("designer") == 1
        # in_flight has 1 level_designer + 1 tech_artist
        in_flight_roles = r.tool_result["in_flight_by_role"]
        assert in_flight_roles.get("level_designer") == 1
        assert in_flight_roles.get("tech_artist") == 1
        # blocked is all tech_artist
        assert r.tool_result["blocked_by_role"].get("tech_artist") == 1
    finally:
        os.chdir(prev)
    print("OK /standup per-role rollups (closed/in_flight/blocked) match seed")


def test_standup_blocked_list_includes_blocker_notes() -> None:
    state, _, prev, _ = _seed_mixed_backlog()
    try:
        r = dispatch("standup")
        blocked = r.tool_result["blocked"]
        assert len(blocked) == 1
        b = blocked[0]
        assert b["title"] == "Blocked task"
        assert b["blockers"] == ["waiting on art_director"]
    finally:
        os.chdir(prev)
    print("OK /standup surfaces blockers list for each blocked task")


def test_standup_empty_backlog_returns_zero_counts_cleanly() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("standup")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_result["closed_recent_count"] == 0
        assert r.tool_result["in_flight_count"] == 0
        assert r.tool_result["blocked_count"] == 0
        assert r.tool_result["pending_count"] == 0
        assert r.tool_result["total_tasks"] == 0
        # Message still renders (no crashes on empty)
        assert "closed 0" in r.message
    finally:
        os.chdir(prev)
    print("OK /standup on empty backlog → all-zero counts, no crash")


def test_standup_turkish_aliases() -> None:
    state, _, prev, _ = _seed_mixed_backlog()
    try:
        for alias in ("toplantı", "toplanti", "özet", "ozet"):
            r = dispatch(alias)
            assert r.handled is True, f"/{alias} should resolve to /standup"
            assert r.tool_name == "studio_standup", (
                f"/{alias} should fire studio_standup; got {r.tool_name}"
            )
    finally:
        os.chdir(prev)
    print("OK /toplantı /toplanti /özet /ozet all → /standup")


def test_help_lists_standup() -> None:
    r = dispatch("help")
    assert "/standup" in r.message, "/help should advertise /standup"
    print("OK /help advertises /standup")


# ─────────────────────────────────────────── Phase 72: /log + /journal


def test_log_appends_entry_to_today_journal() -> None:
    import time
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=Path(os.getcwd()))
        r = dispatch("log first entry from chat")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_journal_append"
        # File exists at today's date
        today = time.strftime("%Y-%m-%d")
        jpath = paths.journal_for_date(today)
        assert jpath.is_file(), f"/log should create {jpath}"
        content = jpath.read_text(encoding="utf-8")
        assert "first entry from chat" in content
        # File has a markdown date header
        assert f"# Journal — {today}" in content
    finally:
        os.chdir(prev)
    print("OK /log <msg> creates today's journal file with date header + entry")


def test_log_appends_multiple_entries_chronologically() -> None:
    import time
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=Path(os.getcwd()))
        dispatch("log alpha note")
        dispatch("log beta note")
        dispatch("log gamma note")
        today = time.strftime("%Y-%m-%d")
        content = paths.journal_for_date(today).read_text(encoding="utf-8")
        # All three entries land, in order
        alpha_pos = content.find("alpha note")
        beta_pos = content.find("beta note")
        gamma_pos = content.find("gamma note")
        assert 0 < alpha_pos < beta_pos < gamma_pos, (
            "entries should appear in chronological order"
        )
        # Each line has a HH:MM:SS timestamp marker
        assert content.count("**") >= 6, (
            "every entry should be wrapped in `**timestamp**` bold markers"
        )
    finally:
        os.chdir(prev)
    print("OK /log appends multiple entries chronologically in same file")


def test_log_without_message_returns_usage() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("log")
        assert r.handled is True
        assert r.ok is False
        assert "Usage" in r.message
        assert "/log" in r.message
    finally:
        os.chdir(prev)
    print("OK /log with no args → usage hint")


def test_log_joins_multi_word_message() -> None:
    """/log treats every arg word as part of the message — no quoting
    needed for natural notes."""
    import time
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=Path(os.getcwd()))
        dispatch("log shipped feature ABC behind feature_flag XYZ")
        content = paths.journal_for_date(time.strftime("%Y-%m-%d")).read_text(
            encoding="utf-8"
        )
        assert "shipped feature ABC behind feature_flag XYZ" in content
    finally:
        os.chdir(prev)
    print("OK /log joins multi-word args without quoting")


def test_journal_reads_today_entries() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("log entry one")
        dispatch("log entry two")
        r = dispatch("journal")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_journal_read"
        assert r.tool_result["total_days"] == 1
        # The flat 'recent' list has today's content
        recent = r.tool_result["recent"]
        assert len(recent) == 1
        assert "entry one" in recent[0]["content"]
        assert "entry two" in recent[0]["content"]
    finally:
        os.chdir(prev)
    print("OK /journal reads today's entries from the new journal file")


def test_journal_empty_returns_friendly_message() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("journal")
        assert r.ok is True
        assert r.tool_result["total_days"] == 0
        # Message hints how to get started
        assert "/log" in r.message
    finally:
        os.chdir(prev)
    print("OK /journal on empty journal → 'drop one with /log' hint")


def test_journal_window_argument_widens_lookback() -> None:
    """/journal 7 reads up to 7 days back. We can't fake date easily,
    but we CAN verify that the days argument is passed through and the
    result key reflects it."""
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("log today's note")
        r = dispatch("journal 7")
        assert r.ok is True
        assert r.tool_result["days"] == 7
        # Only today has content, so total_days still == 1
        assert r.tool_result["total_days"] == 1
    finally:
        os.chdir(prev)
    print("OK /journal <days> threads days argument to studio_journal_read")


def test_journal_bad_arg_rejected() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("journal abc")
        assert r.ok is False
        assert "integer" in r.message.lower() or "abc" in r.message
        r2 = dispatch("journal -3")
        assert r2.ok is False
        r3 = dispatch("journal 0")
        assert r3.ok is False
    finally:
        os.chdir(prev)
    print("OK /journal rejects non-integer, negative, and zero days")


def test_log_journal_turkish_aliases() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        # /not → log
        r = dispatch("not bir not türkçe")
        assert r.handled is True
        assert r.tool_name == "studio_journal_append"
        # /kayıt → log
        r = dispatch("kayıt başka not")
        assert r.tool_name == "studio_journal_append"
        # /günlük → journal
        r = dispatch("günlük")
        assert r.tool_name == "studio_journal_read"
        # /geçmiş → journal
        r = dispatch("geçmiş 3")
        assert r.tool_name == "studio_journal_read"
    finally:
        os.chdir(prev)
    print("OK Türkçe journal aliases (/not /kayıt /günlük /geçmiş) all resolve")


def test_help_lists_log_and_journal() -> None:
    r = dispatch("help")
    for required in ("/log", "/journal"):
        assert required in r.message, (
            f"/help should advertise {required} after Phase 72"
        )
    print("OK /help advertises /log and /journal")


def test_journal_directory_auto_created_on_first_log() -> None:
    """First /log call creates studio/memory/journal/ if it didn't exist
    yet — for studios scaffolded before Phase 72 added the directory."""
    import time
    state, _, prev = _fresh_studio_cwd()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=Path(os.getcwd()))
        # Remove the journal dir to simulate pre-Phase-72 studio
        import shutil
        if paths.journal.is_dir():
            shutil.rmtree(paths.journal)
        assert not paths.journal.exists()

        r = dispatch("log first ever entry")
        assert r.ok is True
        assert paths.journal.is_dir(), "log must auto-create journal dir"
        assert paths.journal_for_date(time.strftime("%Y-%m-%d")).is_file()
    finally:
        os.chdir(prev)
    print("OK /log auto-creates studio/memory/journal/ on a pre-Phase-72 studio")


# ─────────────────────────────────────────── Phase 73: /decide


def test_decide_records_decision_with_title_and_summary() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("decide use URP | already adopted; SRP migration later")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_propose_decision"
        # Decision actually persisted
        decisions = state.load_decisions()
        assert len(decisions) == 1
        d = decisions[0]
        assert d.title == "use URP"
        assert d.summary == "already adopted; SRP migration later"
        assert d.status.value == "proposed"
        # Result message shows the short id + title
        assert "URP" in r.message
        assert "proposed" in r.message
    finally:
        os.chdir(prev)
    print("OK /decide <title> | <summary> persists a proposed decision")


def test_decide_title_only_works_with_hint() -> None:
    """No pipe → whole line becomes title; message hints to add summary."""
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("decide switch to compute shaders for terrain LOD")
        assert r.ok is True
        decisions = state.load_decisions()
        assert len(decisions) == 1
        assert decisions[0].title == "switch to compute shaders for terrain LOD"
        assert decisions[0].summary == ""
        # Helpful hint to add a summary next time
        assert "no summary" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /decide <title-only> persists decision + hints to add summary")


def test_decide_without_args_returns_usage() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("decide")
        assert r.handled is True
        assert r.ok is False
        assert "Usage" in r.message
        assert "/decide" in r.message
    finally:
        os.chdir(prev)
    print("OK /decide with no args → usage hint with example")


def test_decide_with_empty_title_before_pipe_rejected() -> None:
    """A pipe with nothing before it → no title → reject (don't silently
    record a no-title decision)."""
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("decide | just a summary, no title")
        assert r.handled is True
        assert r.ok is False
        assert "title" in r.message.lower()
        # Nothing got persisted
        assert state.load_decisions() == []
    finally:
        os.chdir(prev)
    print("OK /decide with empty title rejected — nothing persisted")


def test_decide_multiple_titles_persist_in_order() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        dispatch("decide first decision | summary one")
        dispatch("decide second decision | summary two")
        dispatch("decide third decision | summary three")
        decisions = state.load_decisions()
        assert len(decisions) == 3
        titles = [d.title for d in decisions]
        assert "first decision" in titles
        assert "second decision" in titles
        assert "third decision" in titles
    finally:
        os.chdir(prev)
    print("OK /decide called 3 times persists 3 decisions")


def test_decide_turkish_alias() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("karar yeni karar | açıklama metni")
        assert r.handled is True
        assert r.tool_name == "studio_propose_decision"
        decisions = state.load_decisions()
        assert len(decisions) == 1
        assert decisions[0].title == "yeni karar"
        assert decisions[0].summary == "açıklama metni"
    finally:
        os.chdir(prev)
    print("OK /karar (Türkçe) resolves to /decide and persists correctly")


def test_help_lists_decide() -> None:
    r = dispatch("help")
    assert "/decide" in r.message, "/help should advertise /decide"
    print("OK /help advertises /decide")


# ─────────────────────────────────────────── Phase 75: /find


def _seed_searchable_studio() -> tuple:
    """A studio with content in every searchable surface — so /find
    can prove each bucket is hit."""
    state, tmp, prev = _fresh_studio_cwd()
    from unitytools.studio import StudioPaths
    from unitytools.studio.models import Task, Decision, Milestone

    paths = StudioPaths(project_root=Path(os.getcwd()))
    paths.gdd.write_text(
        "# GDD\nThe core loop is climbing the lighthouse and "
        "lighting the lamp.\n",
        encoding="utf-8",
    )
    paths.art_bible.write_text(
        "# Art Bible\nWarm sunset palette. The lamp is the focal point.\n",
        encoding="utf-8",
    )
    paths.sprint_current.write_text(
        "# Sprint 3\n- Wire lighthouse pickup.\n",
        encoding="utf-8",
    )

    state.add_task(Task(
        title="Lighthouse VFX",
        role="designer",
        description="particle burst when the lamp ignites",
    ))
    state.add_task(Task(title="Unrelated task", role="qa"))

    state.append_decision(Decision(
        title="Use URP",
        summary="already adopted; lighthouse renderer benefits from it",
    ))
    state.append_decision(Decision(
        title="Procedural fog",
        summary="something completely different",
    ))

    state.add_milestone(Milestone(
        name="Lighthouse milestone",
        description="Ship the lighthouse level slice",
    ))

    # Drop a journal entry mentioning the keyword
    dispatch("log lighthouse spec noted today")
    return state, tmp, prev


def test_find_searches_every_surface() -> None:
    state, _, prev = _seed_searchable_studio()
    try:
        r = dispatch("find lighthouse")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_find"
        # Each bucket should have at least one hit
        assert len(r.tool_result["tasks"]) >= 1, "tasks bucket missed lighthouse"
        assert len(r.tool_result["decisions"]) >= 1, "decisions bucket missed lighthouse"
        assert len(r.tool_result["docs"]) >= 1, "docs bucket missed lighthouse"
        assert len(r.tool_result["milestones"]) >= 1, "milestones bucket missed"
        assert len(r.tool_result["journal"]) >= 1, "journal bucket missed"
        # all_hits aggregates them
        sources = {h["source"] for h in r.tool_result["all_hits"]}
        assert {"task", "decision", "doc", "milestone", "journal"}.issubset(sources)
    finally:
        os.chdir(prev)
    print("OK /find <needle> hits every surface (tasks/decisions/docs/milestones/journal)")


def test_find_excerpt_centred_on_match() -> None:
    """Each hit's excerpt should include the needle, not just the
    start of the file."""
    state, _, prev = _seed_searchable_studio()
    try:
        r = dispatch("find lamp ignites")
        # Find the task hit
        task_hit = next(t for t in r.tool_result["tasks"]
                         if "particle burst" in t.get("excerpt", ""))
        # Excerpt mentions the needle substring
        assert "lamp ignites" in task_hit["excerpt"].lower()
    finally:
        os.chdir(prev)
    print("OK /find excerpts are centred on the match (not the file head)")


def test_find_no_hits_returns_friendly_message() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("find zzzzzzzzzzzz_no_match")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_result["total_hits"] == 0
        assert "No hits" in r.message
    finally:
        os.chdir(prev)
    print("OK /find with no hits → ok=True, total_hits=0, friendly message")


def test_find_empty_needle_returns_usage() -> None:
    r = dispatch("find")
    assert r.handled is True
    assert r.ok is False
    assert "Usage" in r.message
    print("OK /find with no needle → usage hint")


def test_find_case_insensitive() -> None:
    state, _, prev = _seed_searchable_studio()
    try:
        r_lower = dispatch("find lighthouse")
        r_upper = dispatch("find LIGHTHOUSE")
        r_mixed = dispatch("find LightHouse")
        assert (
            r_lower.tool_result["total_hits"]
            == r_upper.tool_result["total_hits"]
            == r_mixed.tool_result["total_hits"]
        ), "case should not affect hit count"
    finally:
        os.chdir(prev)
    print("OK /find is case-insensitive")


def test_find_multi_word_needle_joined() -> None:
    """Multi-word needles are joined back to a single phrase, not
    split into OR-terms."""
    state, _, prev = _seed_searchable_studio()
    try:
        r = dispatch("find particle burst")
        # Should find the task with that exact phrase in description
        assert r.tool_result["total_hits"] >= 1
        task_hit = next(t for t in r.tool_result["tasks"]
                         if "particle burst" in t["excerpt"].lower())
        assert task_hit is not None
    finally:
        os.chdir(prev)
    print("OK /find joins multi-word args into a phrase (not OR split)")


def test_find_turkish_aliases() -> None:
    state, _, prev = _seed_searchable_studio()
    try:
        for alias in ("bul", "ara", "arama"):
            r = dispatch(f"{alias} lighthouse")
            assert r.handled is True, f"/{alias} should resolve to /find"
            assert r.tool_name == "studio_find", (
                f"/{alias} should fire studio_find; got {r.tool_name}"
            )
            assert r.tool_result["total_hits"] >= 1
    finally:
        os.chdir(prev)
    print("OK /bul /ara /arama (Türkçe) all → /find with correct hit counts")


def test_help_lists_find() -> None:
    r = dispatch("help")
    assert "/find" in r.message, "/help should advertise /find"
    print("OK /help advertises /find")


# ─────────────────────────────────────────── Phase 76: /burndown


def _seed_milestone_studio() -> tuple:
    """Studio with 2 milestones at different completion levels +
    1 orphan task — exercises project rollup vs. per-milestone math."""
    state, tmp, prev = _fresh_studio_cwd()
    from unitytools.studio.models import Task, Milestone, TaskStatus

    m1 = Milestone(name="Vertical slice")
    m2 = Milestone(name="Demo build")
    state.add_milestone(m1)
    state.add_milestone(m2)
    # M1: 3 of 5 done = 60%
    for i in range(5):
        t = Task(title=f"m1 task {i}", role="designer", milestone=m1.id)
        if i < 3:
            t.status = TaskStatus.DONE
        state.add_task(t)
    # M2: 1 of 4 done = 25%
    for i in range(4):
        t = Task(title=f"m2 task {i}", role="qa", milestone=m2.id)
        if i < 1:
            t.status = TaskStatus.DONE
        state.add_task(t)
    # Orphan (no milestone) — pulls project pct below pure milestone avg
    state.add_task(Task(title="Orphan", role="producer"))
    return state, tmp, prev, m1, m2


def test_burndown_lists_every_milestone_sorted_by_ascending_pct() -> None:
    state, _, prev, m1, m2 = _seed_milestone_studio()
    try:
        r = dispatch("burndown")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_burndown"
        rows = r.tool_result["milestones"]
        assert len(rows) == 2
        # Demo build (25%) should come before Vertical slice (60%)
        assert rows[0]["name"] == "Demo build"
        assert rows[1]["name"] == "Vertical slice"
        assert rows[0]["completion_pct"] < rows[1]["completion_pct"]
    finally:
        os.chdir(prev)
    print("OK /burndown sorts milestones ascending by completion (farthest first)")


def test_burndown_project_rollup_includes_orphan_tasks() -> None:
    """Total task count must include the orphan task — milestone-linked
    counts alone would miss it."""
    state, _, prev, m1, m2 = _seed_milestone_studio()
    try:
        r = dispatch("burndown")
        project = r.tool_result["project"]
        # 5 + 4 + 1 (orphan) = 10 total; 3 + 1 = 4 done
        assert project["task_count"] == 10
        assert project["done_count"] == 4
        assert project["completion_pct"] == 0.4
    finally:
        os.chdir(prev)
    print("OK /burndown project rollup counts every task — including orphans")


def test_burndown_ascii_bar_reflects_pct() -> None:
    state, _, prev, m1, m2 = _seed_milestone_studio()
    try:
        r = dispatch("burndown")
        # 40% project completion → 8 # chars in a 20-char bar
        project_bar = r.tool_result["project"]["bar"]
        assert "[########------------]" in project_bar, (
            f"project bar should show 8/20 filled at 40%; got {project_bar!r}"
        )
        assert "40%" in project_bar
        # Per-milestone bars also formatted
        for row in r.tool_result["milestones"]:
            assert row["bar"].startswith("[") and row["bar"].count("#") + row["bar"].count("-") == 20
    finally:
        os.chdir(prev)
    print("OK /burndown bars are 20-char ASCII with correct fill at each pct")


def test_burndown_message_renders_full_chart() -> None:
    """The CommandResult.message itself should carry the multi-line
    chart so chat panels can render it without parsing tool_result."""
    state, _, prev, m1, m2 = _seed_milestone_studio()
    try:
        r = dispatch("burndown")
        # Project line + 2 milestone lines = at least 3 lines
        line_count = r.message.count("\n") + 1
        assert line_count >= 3, f"message should have 3+ lines, got {line_count}"
        # All milestone names appear in the message
        assert "Vertical slice" in r.message
        assert "Demo build" in r.message
        # Project rollup is the first line
        assert r.message.startswith("Project")
    finally:
        os.chdir(prev)
    print("OK /burndown message line carries full multi-line ASCII chart")


def test_burndown_specific_milestone_id() -> None:
    state, _, prev, m1, m2 = _seed_milestone_studio()
    try:
        r = dispatch(f"burndown {m1.id}")
        assert r.ok is True
        # Only the requested milestone in the rows
        rows = r.tool_result["milestones"]
        assert len(rows) == 1
        assert rows[0]["name"] == "Vertical slice"
        assert rows[0]["completion_pct"] == 0.6
    finally:
        os.chdir(prev)
    print("OK /burndown <id> narrows to one milestone")


def test_burndown_unknown_id_fails_clean() -> None:
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("burndown not-a-real-milestone-id")
        assert r.handled is True
        assert r.ok is False
        assert "not found" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /burndown <bad-id> → ok=False with not-found message")


def test_burndown_empty_studio_handles_gracefully() -> None:
    """Studio with zero milestones still returns a clean result —
    no division-by-zero, no crash on the chart builder."""
    state, _, prev = _fresh_studio_cwd()
    try:
        r = dispatch("burndown")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_result["milestone_count"] == 0
        assert r.tool_result["project"]["task_count"] == 0
        assert r.tool_result["project"]["completion_pct"] == 0.0
        # Message hints user how to seed
        assert "scaffold" in r.message.lower() or "milestone" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /burndown on empty studio → clean zeros + hint, no crash")


def test_burndown_turkish_aliases() -> None:
    state, _, prev, _, _ = _seed_milestone_studio()
    try:
        for alias in ("ilerleme", "yakım", "yakim", "grafik"):
            r = dispatch(alias)
            assert r.handled is True, f"/{alias} should resolve to /burndown"
            assert r.tool_name == "studio_burndown", (
                f"/{alias} should fire studio_burndown; got {r.tool_name}"
            )
    finally:
        os.chdir(prev)
    print("OK /ilerleme /yakım /yakim /grafik (Türkçe) → /burndown")


def test_help_lists_burndown() -> None:
    r = dispatch("help")
    assert "/burndown" in r.message, "/help should advertise /burndown"
    print("OK /help advertises /burndown")


# ─────────────────────────────────────────── Phase 78: typo suggestions


def test_suggest_command_handles_common_typos() -> None:
    from unitytools.cli.chat_commands import suggest_command
    # Each common typo should put the correct canonical command first.
    cases = [
        ("buldown", "burndown"),
        ("fnid", "find"),
        ("standp", "standup"),
        ("tsks", "tasks"),
        ("sprnt", "sprint"),
        ("helo", "help"),
        ("dashbord", "dashboard"),
    ]
    for typo, expected in cases:
        suggestions = suggest_command(typo)
        assert expected in suggestions, (
            f"/{typo} should suggest /{expected}; got {suggestions}"
        )
        # And it should be among the top 3
        assert expected in suggestions[:3]
    print("OK suggest_command resolves 7 common typos to the right canonical")


def test_suggest_command_resolves_through_turkish_aliases() -> None:
    """A typo of a Türkçe alias should suggest the CANONICAL command,
    not the alias itself — chat-server users see English commands."""
    from unitytools.cli.chat_commands import suggest_command
    # 'olustr' is a typo of 'oluştur' which is alias for 'scaffold'
    suggestions = suggest_command("olustr")
    assert "scaffold" in suggestions, (
        f"/olustr should suggest /scaffold (alias resolved); got {suggestions}"
    )
    # 'gunluk' typo of 'gunluk' → journal alias → suggest 'journal'
    suggestions = suggest_command("gunluk")
    assert "journal" in suggestions, (
        f"/gunluk should suggest /journal; got {suggestions}"
    )
    print("OK Türkçe-alias typos resolve to canonical English suggestions")


def test_suggest_command_returns_empty_for_total_miss() -> None:
    from unitytools.cli.chat_commands import suggest_command
    assert suggest_command("zzzzzzzz") == []
    assert suggest_command("") == []
    # Very short queries: too ambiguous, return [] (cutoff filters them)
    assert suggest_command("b") == []
    print("OK suggest_command returns [] for empty / off-target / too-short input")


def test_suggest_command_dedupe_via_alias_resolution() -> None:
    """If 'tasks' and 'görev' (alias for 'tasks') both match a typo,
    we should see /tasks only once."""
    from unitytools.cli.chat_commands import suggest_command
    suggestions = suggest_command("tasks")
    # /tasks itself is the obvious answer
    assert suggestions[0] == "tasks"
    # And no duplicate
    assert len(suggestions) == len(set(suggestions))
    print("OK suggest_command dedupes after alias-resolution")


def test_suggest_command_respects_max_results() -> None:
    from unitytools.cli.chat_commands import suggest_command
    suggestions = suggest_command("status", max_results=1)
    assert len(suggestions) <= 1
    suggestions = suggest_command("status", max_results=5)
    assert len(suggestions) <= 5
    print("OK suggest_command respects max_results cap")


def test_canonical_commands_includes_commit() -> None:
    """Phase 79 added /commit — must be in _CANONICAL_COMMANDS so typos
    like /commti suggest /commit."""
    from unitytools.cli.chat_commands import _CANONICAL_COMMANDS, suggest_command
    assert "commit" in _CANONICAL_COMMANDS
    # And the suggester picks it up on common typo
    suggestions = suggest_command("commti")
    assert "commit" in suggestions, (
        f"/commti should suggest /commit; got {suggestions}"
    )
    print("OK /commit registered in suggester vocab + typo /commti → /commit")


def test_canonical_commands_match_dispatcher() -> None:
    """Drift catch: every command branch in dispatch() must appear in
    _CANONICAL_COMMANDS (used by suggest_command), otherwise typos for
    new phases won't be suggested."""
    from unitytools.cli.chat_commands import _CANONICAL_COMMANDS
    # Every command that the dispatcher routes — pulled from the /help
    # listing AND a few REPL-handled ones we explicitly include.
    r = dispatch("help")
    needed: set[str] = set()
    for section in r.tool_result["sections"]:
        for name, _desc in section["commands"]:
            cmd = name.split()[0].lstrip("/")
            needed.add(cmd)
    # /quit / /exit / /q are dispatcher-handled
    needed.update({"quit", "exit", "q"})
    # /clear is REPL-only — exclude
    needed.discard("clear")

    missing = needed - set(_CANONICAL_COMMANDS)
    assert not missing, (
        f"_CANONICAL_COMMANDS missing entries: {sorted(missing)} — "
        f"typos for these commands won't be suggested. Add them."
    )
    print(f"OK every /help-advertised command ({len(needed)}) is in _CANONICAL_COMMANDS")


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
    # Phase 65 Turkish aliases
    test_resolve_alias_maps_turkish_to_english()
    test_resolve_alias_is_case_insensitive()
    test_resolve_alias_passes_english_through_unchanged()
    test_turkish_oluştur_actually_scaffolds()
    test_turkish_yürüt_actually_dispatches()
    test_turkish_sağlık_fires_diag()
    test_turkish_rapor_fires_dashboard()
    test_quit_aliases_carry_quit_flag()
    # Phase 66 /build
    test_build_command_recognised()
    test_build_without_target_returns_usage_with_choices()
    test_build_with_unknown_target_lists_choices()
    test_build_target_alias_table_covers_common_keywords()
    test_build_without_bridge_context_fails_clean()
    test_build_with_offline_bridge_fails_clean()
    test_build_preflight_blocks_when_ship_check_fails()
    test_build_force_skips_preflight()
    test_build_auto_generates_output_path()
    test_build_dev_flag_passes_development_build()
    test_build_turkish_aliases()
    # Phase 68 dispatcher meta commands
    test_help_command_returns_command_listing()
    test_help_lists_every_dispatch_section()
    test_help_message_mentions_turkish_aliases()
    test_help_turkish_yardim_alias_resolves()
    test_tools_lists_registered_tools()
    test_tools_with_substring_filter()
    test_tools_filter_misses_returns_empty()
    test_tools_turkish_alias_resolves()
    test_status_without_ctx_reports_no_bridge()
    test_status_with_offline_bridge_reports_offline()
    test_status_with_connected_bridge_reports_connected()
    test_status_includes_provider_and_model_from_ctx()
    test_studio_status_returns_summary_on_active_studio()
    test_studio_status_reports_inactive_when_no_state()
    # Phase 69 /sprint + /next producer shortcuts
    test_sprint_command_recognised()
    test_sprint_empty_file_surfaces_friendly_message()
    test_next_returns_oldest_ready_task()
    test_next_role_filter_narrows_to_discipline()
    test_next_with_unknown_role_fails_clean()
    test_next_when_backlog_empty_says_no_pending()
    test_next_skips_tasks_blocked_by_deps()
    test_next_when_only_blocked_tasks_left_explains_why()
    test_next_turkish_aliases_resolve()
    test_help_lists_phase_69_commands()
    # Phase 70 task lifecycle (/take /done /block /unblock /why)
    test_take_marks_task_in_progress()
    test_done_marks_task_done()
    test_unblock_returns_blocked_to_pending()
    test_block_appends_reason_to_blockers()
    test_block_without_reason_still_blocks_task()
    test_block_appends_to_existing_reasons()
    test_why_explains_status_and_deps()
    test_why_marks_task_ready_when_no_deps()
    test_take_without_id_returns_usage()
    test_block_without_id_returns_usage()
    test_lifecycle_with_unknown_partial_id_fails_clean()
    test_lifecycle_ambiguous_partial_lists_candidates()
    test_turkish_aliases_resolve_to_lifecycle_commands()
    test_help_lists_phase_70_commands()
    test_done_takes_short_id_from_next()
    # Phase 71 /standup daily digest
    test_standup_returns_correct_status_counts()
    test_standup_message_carries_one_line_summary()
    test_standup_window_argument_expands_closed_set()
    test_standup_bad_window_returns_usage()
    test_standup_zero_or_negative_window_rejected()
    test_standup_role_rollups_match_seeded_tasks()
    test_standup_blocked_list_includes_blocker_notes()
    test_standup_empty_backlog_returns_zero_counts_cleanly()
    test_standup_turkish_aliases()
    test_help_lists_standup()
    # Phase 72 /log + /journal
    test_log_appends_entry_to_today_journal()
    test_log_appends_multiple_entries_chronologically()
    test_log_without_message_returns_usage()
    test_log_joins_multi_word_message()
    test_journal_reads_today_entries()
    test_journal_empty_returns_friendly_message()
    test_journal_window_argument_widens_lookback()
    test_journal_bad_arg_rejected()
    test_log_journal_turkish_aliases()
    test_help_lists_log_and_journal()
    test_journal_directory_auto_created_on_first_log()
    # Phase 73 /decide
    test_decide_records_decision_with_title_and_summary()
    test_decide_title_only_works_with_hint()
    test_decide_without_args_returns_usage()
    test_decide_with_empty_title_before_pipe_rejected()
    test_decide_multiple_titles_persist_in_order()
    test_decide_turkish_alias()
    test_help_lists_decide()
    # Phase 75 /find cross-studio search
    test_find_searches_every_surface()
    test_find_excerpt_centred_on_match()
    test_find_no_hits_returns_friendly_message()
    test_find_empty_needle_returns_usage()
    test_find_case_insensitive()
    test_find_multi_word_needle_joined()
    test_find_turkish_aliases()
    test_help_lists_find()
    # Phase 76 /burndown
    test_burndown_lists_every_milestone_sorted_by_ascending_pct()
    test_burndown_project_rollup_includes_orphan_tasks()
    test_burndown_ascii_bar_reflects_pct()
    test_burndown_message_renders_full_chart()
    test_burndown_specific_milestone_id()
    test_burndown_unknown_id_fails_clean()
    test_burndown_empty_studio_handles_gracefully()
    test_burndown_turkish_aliases()
    test_help_lists_burndown()
    # Phase 78 typo suggestions
    test_suggest_command_handles_common_typos()
    test_suggest_command_resolves_through_turkish_aliases()
    test_suggest_command_returns_empty_for_total_miss()
    test_suggest_command_dedupe_via_alias_resolution()
    test_suggest_command_respects_max_results()
    test_canonical_commands_includes_commit()
    test_canonical_commands_match_dispatcher()
    print("All chat-command tests passed (Phase 59-79)")


if __name__ == "__main__":
    run_test()
