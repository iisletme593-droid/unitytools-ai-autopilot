"""Phase 74: JSON-serialization invariant for slash command dispatch.

Slash commands are dispatched both from the REPL (no serialization
needed) and the chat-server (Phase 67), which JSON-encodes every
CommandResult.tool_result and emits it as a `tool_result` event over
the socket. If any handler leaks a non-JSON-encodable value into
tool_result (Path, datetime, set, dataclass instance, etc.), the
server crashes the connection.

The Phase 67 test uses `json.dumps(..., default=str)` to coerce
unencodable types — that hides bugs. This file dispatches every
recognised slash command and asserts the result is JSON-encodable
WITHOUT a default fallback.

Every slash command that's added in future phases should pass this
test by construction. Failing tests here mean a dispatcher is
returning a Path / datetime / custom object instead of primitives.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.cli.chat_commands import (
    CommandResult,
    DispatchContext,
    dispatch,
)
from unitytools.studio import StudioPaths, StudioState, init_studio_tools
from unitytools.studio.models import Task, TaskStatus


def _seed_studio() -> tuple[StudioState, Path, str]:
    """Build a richer studio with tasks of every status so commands
    like /standup and /next return non-empty results."""
    prev_cwd = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="ph74-ser-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    # Plant content for commands that read files
    paths.gdd.write_text("# GDD\nA pitch.\n", encoding="utf-8")
    paths.sprint_current.write_text("# Sprint X\n- task A\n", encoding="utf-8")

    # One task per status — exercises every count branch
    now = time.time()
    pending = Task(title="Pending task", role="designer")
    state.add_task(pending)
    inflight = Task(title="In progress", role="level_designer",
                     status=TaskStatus.IN_PROGRESS)
    state.add_task(inflight)
    blocked = Task(title="Blocked", role="tech_artist",
                    status=TaskStatus.BLOCKED, blockers=["external dep"])
    state.add_task(blocked)
    done = Task(title="Done", role="designer", status=TaskStatus.DONE)
    done.updated_at = now - 3600
    state.add_task(done)

    # One decision so /decisions returns content
    from unitytools.studio.models import Decision
    state.append_decision(Decision(title="Use URP", summary="legacy reasons"))

    os.chdir(tmp)
    return state, tmp, prev_cwd


def _assert_strict_json(payload: Any, where: str) -> None:
    """Assert payload encodes to JSON WITHOUT a default fallback.

    json.dumps with default=None is the strict mode — raises TypeError
    if anything in the tree isn't natively serializable. That's what
    we want to enforce since the chat-server emits each tool_result
    over the wire as the raw payload dict.
    """
    try:
        json.dumps(payload, ensure_ascii=False)
    except TypeError as exc:
        raise AssertionError(
            f"{where}: tool_result contains a non-JSON-encodable value: {exc}. "
            f"Found type leak — coerce to str/int/float/bool/dict/list before "
            f"returning from the dispatcher."
        )


def _exercise_command(
    state: StudioState,
    line: str,
    ctx: DispatchContext | None = None,
    expected_handled: bool = True,
) -> CommandResult:
    """Run one slash line and assert the result is JSON-encodable."""
    r = dispatch(line, ctx=ctx)
    assert r.handled is expected_handled, (
        f"/{line}: handled={r.handled}, expected {expected_handled}"
    )
    # message is always a str
    assert isinstance(r.message, str), (
        f"/{line}: message must be str, got {type(r.message).__name__}"
    )
    # tool_result is optional — when present must be a dict
    if r.tool_result is not None:
        assert isinstance(r.tool_result, dict), (
            f"/{line}: tool_result must be dict, got {type(r.tool_result).__name__}"
        )
        _assert_strict_json(r.tool_result, where=f"/{line}")
    # And the whole CommandResult-as-dict must also be JSON-encodable
    # (this is what the chat-server actually emits as tool_result event)
    _assert_strict_json(
        {
            "handled": r.handled,
            "ok": r.ok,
            "tool_name": r.tool_name,
            "tool_result": r.tool_result,
            "message": r.message,
            "quit": r.quit,
        },
        where=f"/{line} (full CommandResult)",
    )
    return r


# ─────────────────────────────────────── meta / no-state commands


def test_serial_help() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "help")
    finally:
        os.chdir(prev)
    print("OK /help → JSON-encodable")


def test_serial_tools() -> None:
    state, _, prev = _seed_studio()
    try:
        # Bare /tools returns up to 202 entries — make sure those serialize
        _exercise_command(state, "tools")
        # With filter
        _exercise_command(state, "tools studio")
    finally:
        os.chdir(prev)
    print("OK /tools + filter → JSON-encodable")


def test_serial_status() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "status")
        _exercise_command(state, "status", ctx=DispatchContext(unity_bridge=None))

        class FakeBridge:
            def is_connected(self):
                return False

        _exercise_command(state, "status", ctx=DispatchContext(unity_bridge=FakeBridge()))
    finally:
        os.chdir(prev)
    print("OK /status (no ctx / no bridge / fake bridge) → JSON-encodable")


def test_serial_studio() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "studio")
    finally:
        os.chdir(prev)
    print("OK /studio → JSON-encodable")


def test_serial_diag() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "diag")
    finally:
        os.chdir(prev)
    print("OK /diag → JSON-encodable")


# ─────────────────────────────────────── inventory commands


def test_serial_inventory_commands() -> None:
    state, _, prev = _seed_studio()
    try:
        for line in (
            "tasks",
            "tasks pending",
            "milestones",
            "decisions",
            "refs",
            "screenshots",
            "locales",
            "dialogs",
            "assets",
            "roles",
            "behaviours",
            "behaviours combat",
        ):
            _exercise_command(state, line)
    finally:
        os.chdir(prev)
    print("OK every inventory command (tasks/milestones/decisions/refs/...) → JSON-encodable")


# ─────────────────────────────────────── studio actions (no ctx needed)


def test_serial_ship_and_dashboard() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "ship")
        _exercise_command(state, "dashboard")
        _exercise_command(state, "dashboard 1")
    finally:
        os.chdir(prev)
    print("OK /ship + /dashboard → JSON-encodable")


def test_serial_audit_kinds() -> None:
    state, _, prev = _seed_studio()
    try:
        # Each audit kind hits a different aggregator
        for kind in ("lighting", "atmosphere", "vfx", "build",
                      "consistency", "ship", "localization"):
            _exercise_command(state, f"audit {kind}")
    finally:
        os.chdir(prev)
    print("OK every /audit kind → JSON-encodable")


def test_serial_cost() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "cost")
        _exercise_command(state, "cost 30")
    finally:
        os.chdir(prev)
    print("OK /cost (default + days arg) → JSON-encodable")


def test_serial_sync_check_only() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "sync --check")
    finally:
        os.chdir(prev)
    print("OK /sync --check → JSON-encodable")


# ─────────────────────────────────────── Phase 69-73 producer-flow


def test_serial_sprint_next_standup() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "sprint")
        _exercise_command(state, "next")
        _exercise_command(state, "next designer")
        _exercise_command(state, "standup")
        _exercise_command(state, "standup 168")  # weekly
    finally:
        os.chdir(prev)
    print("OK /sprint + /next + /standup → JSON-encodable")


def test_serial_task_lifecycle_commands() -> None:
    """Take/done/unblock/block/why all return task dicts — verify
    every one serializes."""
    state, _, prev = _seed_studio()
    try:
        # Find the seeded pending task
        tasks = state.load_tasks()
        pending = next(t for t in tasks if t.status is TaskStatus.PENDING)
        short = pending.id[:8]
        # take
        _exercise_command(state, f"take {short}")
        # why
        _exercise_command(state, f"why {short}")
        # block + unblock
        _exercise_command(state, f"block {short} test reason")
        _exercise_command(state, f"unblock {short}")
        # done
        _exercise_command(state, f"done {short}")
    finally:
        os.chdir(prev)
    print("OK /take + /done + /unblock + /block + /why → all JSON-encodable")


def test_serial_journal_log() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "log first entry")
        _exercise_command(state, "log second entry with more words")
        _exercise_command(state, "journal")
        _exercise_command(state, "journal 7")
    finally:
        os.chdir(prev)
    print("OK /log + /journal → JSON-encodable")


def test_serial_decide() -> None:
    state, _, prev = _seed_studio()
    try:
        _exercise_command(state, "decide use URP | already adopted")
        _exercise_command(state, "decide title-only decision")
    finally:
        os.chdir(prev)
    print("OK /decide (with + without pipe) → JSON-encodable")


# ─────────────────────────────────────── error paths still serialize


def test_serial_error_paths() -> None:
    """Commands that fail (ok=False) must also produce JSON-encodable
    results — error messages contain user input and tool error dicts."""
    state, _, prev = _seed_studio()
    try:
        # Unknown command
        r = dispatch("not_a_real_command_xyz")
        assert r.handled is False
        _assert_strict_json(
            {"message": r.message, "tool_result": r.tool_result},
            where="unknown command",
        )

        # Bad arg shapes
        for line in (
            "scaffold not_a_genre",
            "audit not_a_kind",
            "build not_a_target",
            "tasks not_a_status",
            "cost not_a_number",
            "dashboard --save not_a_number",
            "take",                     # missing id
            "take zzzzzzzz",            # nonexistent id
            "block",                    # missing id
            "decide",                   # missing args
            "decide | nothing before pipe",
            "standup notanumber",
            "standup -1",
            "journal abc",
            "next not_a_role",
        ):
            r = dispatch(line)
            assert r.handled is True, f"/{line} expected handled=True for error report"
            assert isinstance(r.message, str)
            if r.tool_result is not None:
                _assert_strict_json(r.tool_result, where=f"/{line} (error)")
    finally:
        os.chdir(prev)
    print("OK all error paths produce JSON-encodable CommandResult.tool_result")


# ─────────────────────────────────────── coverage assurance


def test_every_documented_command_is_dispatched() -> None:
    """Drift catch: the /help listing should not advertise a command
    the dispatcher doesn't recognise."""
    r = dispatch("help")
    sections = r.tool_result["sections"]

    # Pull every '/cmd' token out of help and try to dispatch it with
    # safe arguments. We accept handled=True with ok=False (e.g. /scaffold
    # without args returns usage), but handled=False means /help has drift.
    import re

    state, _, prev = _seed_studio()
    try:
        # Build a registry of commands that absolutely need a context or
        # bridge (we skip those — they're tested elsewhere with mocks).
        skip = {
            "/role", "/dispatch", "/build",   # need ctx + bridge / LLM
            "/init",                          # would scaffold another studio
            "/quit",                          # quit flag
        }
        for sec in sections:
            for name, _desc in sec["commands"]:
                cmd_only = name.split()[0]   # e.g. "/decide" from "/decide <title> | <summary>"
                if cmd_only in skip:
                    continue
                line = cmd_only[1:]  # strip leading /
                # Just dispatch with no args — most return usage hints
                r = dispatch(line)
                assert r.handled is True, (
                    f"{cmd_only} in /help but dispatcher returned handled=False"
                )
    finally:
        os.chdir(prev)
    print(f"OK every /help-advertised command (minus 4 ctx-needing) is dispatched")


def run_test() -> None:
    test_serial_help()
    test_serial_tools()
    test_serial_status()
    test_serial_studio()
    test_serial_diag()
    test_serial_inventory_commands()
    test_serial_ship_and_dashboard()
    test_serial_audit_kinds()
    test_serial_cost()
    test_serial_sync_check_only()
    test_serial_sprint_next_standup()
    test_serial_task_lifecycle_commands()
    test_serial_journal_log()
    test_serial_decide()
    test_serial_error_paths()
    test_every_documented_command_is_dispatched()
    print("All Phase 74 JSON-encodability tests passed")


if __name__ == "__main__":
    run_test()
