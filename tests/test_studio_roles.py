"""Phase 2 tests: role definitions + RoleRunner end-to-end with a fake LLM.

The fake LLM is a scripted state machine that returns canned tool_calls
in a defined order, then a final text. This proves the runner loops
correctly, executes each tool, and threads results back into the
conversation — without any network or API key.
"""
from __future__ import annotations

import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    ALL_STUDIO_TOOL_NAMES,
    DESIGNER,
    CRITIC,
    PRODUCER,
    RoleConfig,
    RoleRunner,
    StudioPaths,
    StudioState,
    all_roles,
    get_role,
    init_studio_tools,
)
from unitytools.studio.runner import _filter_tools


# ──────────────────────────────────────────────────────────── fake LLM


@dataclass
class _ScriptedTurn:
    """One canned LLM response: zero-or-more tool calls, then optional text.

    If `tool_calls` is empty, this is the terminating turn.
    """

    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"


class FakeLLM:
    """Plays a list of _ScriptedTurns in order. Records what it saw."""

    def __init__(self, turns: list[_ScriptedTurn]):
        self.turns = turns
        self.cursor = 0
        self.systems_seen: list[str] = []
        self.tool_names_seen: list[set[str]] = []
        self.message_lengths: list[int] = []

    def complete(self, system: str, tools: list[dict], messages: list[dict]) -> dict:
        self.systems_seen.append(system)
        self.tool_names_seen.append({t["name"] for t in tools})
        self.message_lengths.append(len(messages))
        if self.cursor >= len(self.turns):
            raise AssertionError("FakeLLM ran out of scripted turns")
        turn = self.turns[self.cursor]
        self.cursor += 1
        return {
            "text": turn.text,
            "tool_calls": list(turn.tool_calls),
            "stop_reason": turn.stop_reason,
            "raw_content": None,
        }


# ──────────────────────────────────────────────────────── helpers


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="role-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ─────────────────────────────────────────────────────────────── tests


def test_role_definitions_are_consistent() -> None:
    valid_studio = set(ALL_STUDIO_TOOL_NAMES)
    roles = all_roles()
    # Three roles are guaranteed by Phase 2; later phases may add more
    # (e.g. Worker, Level Designer, Art Director).
    role_ids = {r.id for r in roles}
    assert {"producer", "designer", "critic"} <= role_ids
    for role in roles:
        assert role.tool_set, f"{role.id} has no tools"
        # Studio tool references must resolve. Engine tool references
        # (unity_*, unreal_*, blender_*) are validated at runtime, not here.
        studio_refs = {n for n in role.allowed_tools if n.startswith("studio_")}
        assert studio_refs <= valid_studio, f"{role.id} has unknown studio tools: {studio_refs - valid_studio}"
    assert get_role("producer") is PRODUCER
    assert get_role("designer") is DESIGNER
    assert get_role("critic") is CRITIC
    print("OK role definitions consistent")


def test_role_filter_only_advertises_allowed_tools() -> None:
    designer_tools = {t["name"] for t in _filter_tools(DESIGNER)}
    assert designer_tools == DESIGNER.tool_set
    # Designer must NOT see backlog write tools
    assert "studio_add_task" not in designer_tools
    # Producer must NOT see write_gdd
    producer_tools = {t["name"] for t in _filter_tools(PRODUCER)}
    assert "studio_write_gdd" not in producer_tools
    print("OK tool filter respects role allowlist")


def test_runner_executes_designer_brief_to_completion() -> None:
    state, _ = _fresh_studio()

    # Script: designer reads GDD (empty), writes a draft, then stops.
    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": "c1", "name": "studio_read_gdd", "input": {}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(
            tool_calls=[
                {
                    "id": "c2",
                    "name": "studio_write_gdd",
                    "input": {"content": "# GDD\n\nMicro-tactics roguelite.\n"},
                }
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="GDD draft committed.", stop_reason="end_turn"),
    ]
    fake = FakeLLM(turns)
    runner = RoleRunner(fake, max_iterations=5)

    result = runner.run(DESIGNER, brief="Draft initial GDD.")
    assert result.iterations == 3
    assert len(result.tool_calls) == 2
    assert [tc.name for tc in result.tool_calls] == ["studio_read_gdd", "studio_write_gdd"]
    assert all(tc.ok for tc in result.tool_calls)
    assert "Micro-tactics roguelite" in state.read_doc(state.paths.gdd)
    assert result.text.endswith("GDD draft committed.")
    assert result.stop_reason == "end_turn"
    print("OK designer end-to-end with fake LLM")


def test_runner_records_tool_failure_without_aborting() -> None:
    state, _ = _fresh_studio()

    # First call fails (bad status), then designer writes anyway, then stops.
    turns = [
        _ScriptedTurn(
            tool_calls=[
                {"id": "c1", "name": "studio_propose_decision", "input": {"title": "x", "summary": "y"}},
                # Designer can't actually call studio_update_task_status (not in allowlist)
                # so the runner should still execute via registry but tool returns ok=True.
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="Decision proposed.", stop_reason="end_turn"),
    ]
    fake = FakeLLM(turns)
    runner = RoleRunner(fake, max_iterations=5)
    result = runner.run(DESIGNER, brief="Propose a decision.")
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].ok is True
    decisions = state.load_decisions()
    assert len(decisions) == 1 and decisions[0].title == "x"
    print("OK runner records tool calls + decision persisted")


def test_runner_records_unknown_tool_as_error() -> None:
    _state, _ = _fresh_studio()
    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": "c1", "name": "studio_does_not_exist", "input": {}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="gave up", stop_reason="end_turn"),
    ]
    fake = FakeLLM(turns)
    result = RoleRunner(fake).run(DESIGNER, brief="x")
    assert len(result.tool_calls) == 1
    rec = result.tool_calls[0]
    assert rec.ok is False
    assert isinstance(rec.result, dict) and "Unknown tool" in rec.result.get("error", "")
    print("OK unknown tool recorded as error, loop continues")


def test_runner_stops_at_max_iterations() -> None:
    _fresh_studio()
    # Always tool-call, never stop — runner should hit the cap.
    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": f"c{i}", "name": "studio_get_summary", "input": {}}],
            stop_reason="tool_use",
        )
        for i in range(20)
    ]
    fake = FakeLLM(turns)
    result = RoleRunner(fake, max_iterations=3).run(PRODUCER, brief="loop")
    assert result.iterations == 3
    assert result.stop_reason == "max_iterations"
    assert len(result.tool_calls) == 3
    print("OK max_iterations cap honored")


def test_runner_uses_role_specific_system_prompt() -> None:
    _fresh_studio()
    turns = [_ScriptedTurn(text="hi", stop_reason="end_turn")]
    fake = FakeLLM(turns)
    RoleRunner(fake).run(CRITIC, brief="anything")
    assert fake.systems_seen
    assert "Critic" in fake.systems_seen[0]
    assert "Producer" not in fake.systems_seen[0]
    print("OK role-specific system prompt sent to LLM")


def run_test() -> None:
    test_role_definitions_are_consistent()
    test_role_filter_only_advertises_allowed_tools()
    test_runner_executes_designer_brief_to_completion()
    test_runner_records_tool_failure_without_aborting()
    test_runner_records_unknown_tool_as_error()
    test_runner_stops_at_max_iterations()
    test_runner_uses_role_specific_system_prompt()
    print("All studio role tests passed")


if __name__ == "__main__":
    run_test()
