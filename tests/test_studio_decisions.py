"""Phase 15 tests: query_decisions + studio_query_decisions tool.

Symmetric to test_studio_archive's query_archive tests. Verifies the
filter combinations, time windows, search needles, sorting, the LLM
tool's validation behaviour, and the three roles that get the tool.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.studio import (
    CRITIC,
    DESIGNER,
    Decision,
    DecisionStatus,
    PRODUCER,
    StudioPaths,
    StudioState,
    decisions_summary,
    init_studio_tools,
    query_decisions,
)
from unitytools.studio.tools import studio_query_decisions


def _fresh_studio() -> tuple[StudioState, Path]:
    tmp = Path(tempfile.mkdtemp(prefix="dec-test-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    return state, tmp


def _seed_decisions(state: StudioState) -> None:
    now = time.time()
    seeds = [
        # (age_days, author_role, status, title, summary, rationale)
        (1,   "designer",     DecisionStatus.PROPOSED,   "Hex grid combat",         "use hex grids",            "tactical clarity"),
        (10,  "designer",     DecisionStatus.ACCEPTED,   "PS1 lo-fi palette",       "lock palette to PS1",      "consistent mood"),
        (30,  "art_director", DecisionStatus.REJECTED,   "Add VR mode",             "out of scope",             "scope creep risk"),
        (60,  "critic",       DecisionStatus.SUPERSEDED, "Co-op mode",              "single-player only",       "early decision; later changed"),
        (90,  "producer",     DecisionStatus.ACCEPTED,   "Use Ollama provider",     "local-first dev workflow", "no API cost"),
    ]
    for age, role, status, title, summary, rationale in seeds:
        d = Decision(
            title=title,
            summary=summary,
            rationale=rationale,
            author_role=role,
            status=status,
        )
        d.timestamp = now - age * 86400
        state.append_decision(d)


# ───────────────────────────────────────────── basic filters


def test_query_returns_all_newest_first_without_filters() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    out = query_decisions(state)
    assert len(out) == 5
    timestamps = [d.timestamp for d in out]
    assert timestamps == sorted(timestamps, reverse=True)
    print("OK query_decisions default sort + no filter")


def test_query_filters_by_author_role() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    out = query_decisions(state, author_role="designer")
    assert all(d.author_role == "designer" for d in out)
    assert len(out) == 2
    print("OK author_role filter")


def test_query_filters_by_status() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    accepted = query_decisions(state, status=DecisionStatus.ACCEPTED)
    assert all(d.status is DecisionStatus.ACCEPTED for d in accepted)
    assert len(accepted) == 2
    superseded = query_decisions(state, status=DecisionStatus.SUPERSEDED)
    assert len(superseded) == 1
    assert superseded[0].title == "Co-op mode"
    print("OK status filter")


def test_query_filters_compose() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    out = query_decisions(state, author_role="designer", status=DecisionStatus.ACCEPTED)
    assert len(out) == 1
    assert out[0].title == "PS1 lo-fi palette"
    print("OK author_role + status compose")


def test_query_time_window() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    now = time.time()
    # Last 14 days: should catch the 1d and 10d entries
    recent = query_decisions(state, since=now - 14 * 86400)
    assert len(recent) == 2
    # Pre 30 days: should catch the 30d, 60d, 90d entries
    older = query_decisions(state, until=now - 29 * 86400)
    assert len(older) == 3
    print("OK since/until window")


def test_query_search_matches_title_summary_rationale() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    # Title hit
    palette = query_decisions(state, search="palette")
    assert len(palette) == 1
    # Summary hit
    out_of_scope = query_decisions(state, search="out of scope")
    assert len(out_of_scope) == 1
    assert out_of_scope[0].title == "Add VR mode"
    # Rationale hit
    creep = query_decisions(state, search="scope creep")
    assert len(creep) == 1
    # Case-insensitive
    upper = query_decisions(state, search="OLLAMA")
    assert len(upper) == 1
    print("OK search matches title + summary + rationale, case-insensitive")


def test_query_limit_caps_result() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    capped = query_decisions(state, limit=2)
    assert len(capped) == 2
    unbounded = query_decisions(state, limit=0)
    assert len(unbounded) == 5
    print("OK limit cap")


# ───────────────────────────────────────────── empty / edge


def test_query_empty_log_returns_empty_list() -> None:
    state, _ = _fresh_studio()
    out = query_decisions(state)
    assert out == []
    summary = decisions_summary(state)
    assert summary == {"total": 0, "by_status": {}}
    print("OK empty log -> empty result")


def test_decisions_summary_counts_by_status() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    summary = decisions_summary(state)
    assert summary["total"] == 5
    assert summary["by_status"]["accepted"] == 2
    assert summary["by_status"]["proposed"] == 1
    assert summary["by_status"]["rejected"] == 1
    assert summary["by_status"]["superseded"] == 1
    print("OK decisions_summary by_status")


# ───────────────────────────────────────────── tool wrapper


def test_studio_query_decisions_tool_wraps_query() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    result = studio_query_decisions(author_role="designer", limit=10)
    assert result["ok"] is True
    assert result["count"] == 2
    assert result["filters"]["author_role"] == "designer"
    titles = [d["title"] for d in result["decisions"]]
    assert "Hex grid combat" in titles
    assert "PS1 lo-fi palette" in titles
    # Each entry has all the expected fields
    sample = result["decisions"][0]
    for key in ("id", "title", "summary", "rationale", "status", "author_role", "timestamp", "alternatives_considered"):
        assert key in sample
    print("OK studio_query_decisions tool wraps query")


def test_studio_query_decisions_tool_validates_bad_status() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    result = studio_query_decisions(status="nonsense")
    assert result["ok"] is False
    assert "Unknown decision status" in result["error"]
    print("OK bad status -> ok=False, not exception")


def test_studio_query_decisions_search_works_via_tool() -> None:
    state, _ = _fresh_studio()
    _seed_decisions(state)
    result = studio_query_decisions(search="palette")
    assert result["ok"] is True
    assert result["count"] == 1
    assert result["decisions"][0]["title"] == "PS1 lo-fi palette"
    print("OK tool surfaces search filter correctly")


# ───────────────────────────────────────────── role allowlists


def test_query_decisions_in_producer_critic_designer_allowlists() -> None:
    for role in (PRODUCER, CRITIC, DESIGNER):
        assert "studio_query_decisions" in role.tool_set, f"{role.id} missing studio_query_decisions"
    print("OK Producer + Critic + Designer all have studio_query_decisions")


def run_test() -> None:
    test_query_returns_all_newest_first_without_filters()
    test_query_filters_by_author_role()
    test_query_filters_by_status()
    test_query_filters_compose()
    test_query_time_window()
    test_query_search_matches_title_summary_rationale()
    test_query_limit_caps_result()
    test_query_empty_log_returns_empty_list()
    test_decisions_summary_counts_by_status()
    test_studio_query_decisions_tool_wraps_query()
    test_studio_query_decisions_tool_validates_bad_status()
    test_studio_query_decisions_search_works_via_tool()
    test_query_decisions_in_producer_critic_designer_allowlists()
    print("All Phase 15 decisions tests passed")


if __name__ == "__main__":
    run_test()
