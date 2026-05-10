"""Phase 6 calibration tests.

Three things this file proves:

1. Threshold templating: role prompts substitute the values from
   STUDIO_DEFAULTS at module load. Editing config.py changes both the
   prompt text and any code paths that read the same constants.
2. Allowlist sandbox: a misbehaving LLM that emits a tool_call outside
   its role's whitelist is refused at the runner layer, even if the
   tool itself is registered globally and would normally work.
3. Rehearsal (dry-run) mode: a no-API-key LLM walks the doc-only roles
   through real tool calls so disk state changes can be inspected
   end-to-end without burning tokens.
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
    CRITIC,
    DESIGNER,
    LEVEL_DESIGNER,
    PRODUCER,
    STUDIO_DEFAULTS,
    StudioPaths,
    StudioState,
    StudioThresholds,
    WORKER,
    RehearsalLLM,
    RoleRunner,
    has_rehearsal_for,
    init_studio_tools,
    init_studio_unity,
    init_studio_vision,
)


# ─────────────────────────────────────────────────── helpers


@dataclass
class _ScriptedTurn:
    text: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"


class FakeLLM:
    def __init__(self, turns: list[_ScriptedTurn]):
        self.turns = turns
        self.cursor = 0

    def complete(self, system, tools, messages):
        if self.cursor >= len(self.turns):
            raise AssertionError("FakeLLM exhausted")
        turn = self.turns[self.cursor]
        self.cursor += 1
        return {
            "text": turn.text,
            "tool_calls": list(turn.tool_calls),
            "stop_reason": turn.stop_reason,
            "raw_content": None,
        }


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="calib-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


# ──────────────────────────────────────────── threshold templating


def test_role_prompts_show_threshold_values_from_config() -> None:
    """Worker prompt mentions the actual block threshold; Level Designer
    prompt mentions the re-block threshold; Producer mentions the cap on
    new tasks. None of them should still contain {placeholder} braces."""
    block = str(STUDIO_DEFAULTS.worker_block_threshold)
    reblock = str(STUDIO_DEFAULTS.level_designer_reblock_threshold)
    cap = str(STUDIO_DEFAULTS.max_tasks_per_producer_run)

    assert f"composition_match below {block}" in WORKER.system_prompt
    assert f"composition_match is below {reblock}" in LEVEL_DESIGNER.system_prompt
    assert f"more than {cap} new tasks" in PRODUCER.system_prompt
    # No leftover placeholders
    for role in (WORKER, LEVEL_DESIGNER, PRODUCER, DESIGNER, CRITIC):
        assert "{worker_block_threshold}" not in role.system_prompt
        assert "{level_designer_reblock_threshold}" not in role.system_prompt
        assert "{max_tasks_per_producer_run}" not in role.system_prompt
    print("OK threshold values substituted into all prompts")


def test_studio_thresholds_is_a_frozen_dataclass() -> None:
    # Frozen so a typo can't quietly mutate the global default at runtime.
    try:
        STUDIO_DEFAULTS.worker_block_threshold = 0.99  # type: ignore[misc]
    except Exception as exc:  # FrozenInstanceError on dataclass(frozen=True)
        assert "frozen" in str(exc).lower() or "cannot assign" in str(exc).lower()
    else:
        raise AssertionError("STUDIO_DEFAULTS should be immutable")
    # And construction with custom values still works (so future overrides
    # have a path forward).
    custom = StudioThresholds(worker_block_threshold=0.8)
    assert custom.worker_block_threshold == 0.8
    assert custom.level_designer_reblock_threshold == 0.6  # default preserved
    print("OK StudioThresholds is frozen, custom instances allowed")


# ──────────────────────────────────────────── allowlist sandbox


def test_runner_refuses_tool_call_outside_role_allowlist() -> None:
    """Critic does not have studio_write_gdd in its whitelist. Even if the
    LLM hallucinates that tool_call, the runner must refuse to execute it."""
    state, _ = _fresh_studio()
    initial_gdd = state.read_doc(state.paths.gdd)
    turns = [
        _ScriptedTurn(
            tool_calls=[
                {
                    "id": "c1",
                    "name": "studio_write_gdd",
                    "input": {"content": "# HIJACKED\n\nThis should never reach disk.\n"},
                }
            ],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="gave up", stop_reason="end_turn"),
    ]
    runner = RoleRunner(FakeLLM(turns))
    result = runner.run(CRITIC, brief="adversarial")

    assert len(result.tool_calls) == 1
    rec = result.tool_calls[0]
    assert rec.ok is False
    assert isinstance(rec.result, dict)
    assert rec.result.get("error_type") == "ToolNotAllowed"
    # The GDD is unchanged on disk
    assert state.read_doc(state.paths.gdd) == initial_gdd
    print("OK allowlist sandbox refuses out-of-role tool calls")


def test_runner_still_executes_in_allowlist_calls() -> None:
    state, _ = _fresh_studio()
    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": "c1", "name": "studio_get_summary", "input": {}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="ok", stop_reason="end_turn"),
    ]
    runner = RoleRunner(FakeLLM(turns))
    result = runner.run(CRITIC, brief="check")
    assert result.tool_calls[0].ok is True
    assert isinstance(result.tool_calls[0].result, dict) and result.tool_calls[0].result.get("ok") is True
    print("OK allowed calls still pass through")


def test_runner_records_unknown_tool_and_continues() -> None:
    """A tool_call for a name not registered anywhere should be recorded as
    error (not crash). This used to be covered for unknown names that were
    in the allowlist; now we also confirm the runner produces a sensible
    error path even when allowlist contains the (unknown) name."""
    state, _ = _fresh_studio()
    # Designer's allowlist contains studio_propose_decision; add a phantom
    # name that isn't in the registry by monkey-patching the role's tool_set
    # for this test only. (The role definition itself stays clean.)
    from unitytools.studio.roles import RoleConfig
    phantom_role = RoleConfig(
        id="phantom",
        name="Phantom",
        system_prompt="x",
        allowed_tools=("studio_get_summary", "studio_definitely_not_a_tool"),
    )
    turns = [
        _ScriptedTurn(
            tool_calls=[{"id": "c1", "name": "studio_definitely_not_a_tool", "input": {}}],
            stop_reason="tool_use",
        ),
        _ScriptedTurn(text="end", stop_reason="end_turn"),
    ]
    runner = RoleRunner(FakeLLM(turns))
    result = runner.run(phantom_role, brief="x")
    assert result.tool_calls[0].ok is False
    assert "Unknown tool" in result.tool_calls[0].result["error"]
    print("OK unknown-but-allowed tool produces clean error")


# ──────────────────────────────────────────── rehearsal / dry-run


def test_rehearsal_has_scripts_for_doc_only_roles() -> None:
    assert has_rehearsal_for("producer")
    assert has_rehearsal_for("designer")
    assert has_rehearsal_for("critic")
    # Engine roles intentionally have no script — running them dry would
    # write garbage. Dry-run CLI rejects them up front.
    assert not has_rehearsal_for("worker")
    assert not has_rehearsal_for("level_designer")
    assert not has_rehearsal_for("art_director")
    print("OK rehearsal scripts cover the doc-only roles")


def test_rehearsal_drives_designer_to_write_placeholder_gdd() -> None:
    state, _ = _fresh_studio()
    assert state.read_doc(state.paths.gdd) == ""

    runner = RoleRunner(RehearsalLLM("designer"), max_iterations=8)
    result = runner.run(DESIGNER, brief="dry run")
    # The script: get_summary, read_gdd, write_gdd, then end.
    names = [tc.name for tc in result.tool_calls]
    assert names == ["studio_get_summary", "studio_read_gdd", "studio_write_gdd"]
    assert all(tc.ok for tc in result.tool_calls)
    gdd_now = state.read_doc(state.paths.gdd)
    assert "Game Design Document" in gdd_now
    assert "rehearsal placeholder" in gdd_now
    assert result.stop_reason == "end_turn"
    print("OK dry-run designer wrote placeholder GDD without an API call")


def test_rehearsal_skips_steps_not_advertised_to_role() -> None:
    """If a rehearsal step references a tool the role's allowlist excludes,
    the rehearsal should skip it instead of getting blocked by the runner.
    (This guards against rehearsal scripts drifting out of sync with role
    allowlists.)"""
    from unitytools.studio.roles import RoleConfig
    # A locked-down designer that lacks studio_write_gdd: rehearsal should
    # skip the write step and still terminate cleanly.
    locked_designer = RoleConfig(
        id="designer",
        name="Locked Designer",
        system_prompt="locked",
        allowed_tools=("studio_get_summary", "studio_read_gdd"),
    )
    runner = RoleRunner(RehearsalLLM("designer"), max_iterations=8)
    result = runner.run(locked_designer, brief="dry")
    names = [tc.name for tc in result.tool_calls]
    assert "studio_write_gdd" not in names
    # The two read calls still happened
    assert "studio_get_summary" in names
    assert "studio_read_gdd" in names
    print("OK rehearsal skips out-of-allowlist steps gracefully")


def test_rehearsal_unknown_role_returns_helpful_text() -> None:
    state, _ = _fresh_studio()
    runner = RoleRunner(RehearsalLLM("phantom_role_id"))
    result = runner.run(PRODUCER, brief="x")
    assert "no scripted actions" in result.text
    assert result.tool_calls == []
    print("OK rehearsal explicitly tells the user when a role has no script")


def run_test() -> None:
    test_role_prompts_show_threshold_values_from_config()
    test_studio_thresholds_is_a_frozen_dataclass()
    test_runner_refuses_tool_call_outside_role_allowlist()
    test_runner_still_executes_in_allowlist_calls()
    test_runner_records_unknown_tool_and_continues()
    test_rehearsal_has_scripts_for_doc_only_roles()
    test_rehearsal_drives_designer_to_write_placeholder_gdd()
    test_rehearsal_skips_steps_not_advertised_to_role()
    test_rehearsal_unknown_role_returns_helpful_text()
    print("All Phase 6 calibration tests passed")


if __name__ == "__main__":
    run_test()
