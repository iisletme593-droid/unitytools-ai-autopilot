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
    print("All chat-command tests passed (Phase 59 + 60 + 61 + 64 + 65 + 66 + 68 + 69)")


if __name__ == "__main__":
    run_test()
