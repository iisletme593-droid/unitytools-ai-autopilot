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
    find_decision,
    init_studio_tools,
    latest_decisions,
    query_decisions,
    ratify_decision,
)
from unitytools.studio.tools import studio_query_decisions, studio_ratify_decision


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


# ───────────────────────────────── Phase 18: ratify + dedupe + prefix


def test_latest_decisions_dedupes_by_id() -> None:
    """When a decision is re-stated (e.g. ratified), latest_decisions
    returns only the newest row per id; raw load_decisions returns all
    rows for audit."""
    state, _ = _fresh_studio()
    d = Decision(title="Hex grid", summary="use hex", status=DecisionStatus.PROPOSED)
    d.timestamp = time.time() - 100
    state.append_decision(d)

    # Re-state with same id, newer timestamp, different status
    revised = Decision(title="Hex grid", summary="use hex", status=DecisionStatus.ACCEPTED)
    revised.id = d.id
    revised.timestamp = time.time()
    state.append_decision(revised)

    # Raw log still has both rows
    raw = state.load_decisions()
    assert len(raw) == 2
    # Latest-per-id shows only the accepted one
    latest = latest_decisions(state)
    assert len(latest) == 1
    assert latest[0].status is DecisionStatus.ACCEPTED
    print("OK latest_decisions dedupes by id, raw log preserves audit")


def test_ratify_unknown_id_returns_none() -> None:
    state, _ = _fresh_studio()
    assert ratify_decision(state, "no-such-id", DecisionStatus.ACCEPTED) is None
    print("OK ratify unknown id -> None")


def test_ratify_accept_appends_new_row_with_new_status() -> None:
    state, _ = _fresh_studio()
    d = Decision(title="Hex grid", summary="use hex", status=DecisionStatus.PROPOSED, author_role="designer")
    state.append_decision(d)

    revised = ratify_decision(state, d.id, DecisionStatus.ACCEPTED)
    assert revised is not None
    assert revised.id == d.id
    assert revised.status is DecisionStatus.ACCEPTED
    # Title / summary / rationale / author preserved
    assert revised.title == d.title
    assert revised.author_role == d.author_role

    # Audit log has two rows
    assert len(state.load_decisions()) == 2
    # Current view (latest) shows ACCEPTED
    current = latest_decisions(state)
    assert len(current) == 1
    assert current[0].status is DecisionStatus.ACCEPTED
    print("OK ratify accept: appends new row, latest shows accepted")


def test_ratify_reject_path() -> None:
    state, _ = _fresh_studio()
    d = state.append_decision(Decision(title="VR mode", summary="add VR", status=DecisionStatus.PROPOSED))
    revised = ratify_decision(state, d.id, DecisionStatus.REJECTED)
    assert revised.status is DecisionStatus.REJECTED
    assert latest_decisions(state)[0].status is DecisionStatus.REJECTED
    print("OK ratify reject path")


def test_ratify_supersede_links_to_replacement() -> None:
    state, _ = _fresh_studio()
    old = state.append_decision(Decision(title="Co-op", summary="add co-op", status=DecisionStatus.PROPOSED))
    new = state.append_decision(Decision(title="Solo-only", summary="single-player only", status=DecisionStatus.PROPOSED))
    revised = ratify_decision(state, old.id, DecisionStatus.SUPERSEDED, superseded_by=new.id)
    assert revised.status is DecisionStatus.SUPERSEDED
    assert revised.superseded_by == new.id
    print("OK ratify supersede links to replacement id")


def test_query_decisions_reflects_ratified_status() -> None:
    """After ratify, query_decisions shows the new status (not the old
    proposed row)."""
    state, _ = _fresh_studio()
    d = state.append_decision(Decision(title="Hex grid", summary="use hex", status=DecisionStatus.PROPOSED))
    ratify_decision(state, d.id, DecisionStatus.ACCEPTED)

    accepted = query_decisions(state, status=DecisionStatus.ACCEPTED)
    proposed = query_decisions(state, status=DecisionStatus.PROPOSED)
    assert len(accepted) == 1 and accepted[0].id == d.id
    # The original proposed row is NOT surfaced — current state only
    assert len(proposed) == 0
    print("OK query_decisions reflects current state after ratify")


def test_decisions_summary_counts_latest_only() -> None:
    state, _ = _fresh_studio()
    d = state.append_decision(Decision(title="A", summary="s", status=DecisionStatus.PROPOSED))
    ratify_decision(state, d.id, DecisionStatus.ACCEPTED)
    summary = decisions_summary(state)
    # Only the accepted version counts
    assert summary["total"] == 1
    assert summary["by_status"] == {"accepted": 1}
    print("OK decisions_summary counts latest-per-id only")


def test_find_decision_by_exact_id_and_prefix() -> None:
    state, _ = _fresh_studio()
    a = state.append_decision(Decision(title="A", summary="s"))
    # Exact match
    assert find_decision(state, a.id) is not None
    # Unique prefix
    assert find_decision(state, a.id[:6]) is not None
    # No match
    assert find_decision(state, "zzzzzzzz") is None
    # Empty input
    assert find_decision(state, "") is None
    print("OK find_decision: exact + unique prefix + miss + empty")


def test_find_decision_returns_none_on_ambiguous_prefix() -> None:
    """When two ids share a prefix, return None instead of guessing."""
    state, _ = _fresh_studio()
    a = Decision(title="A", summary="s")
    b = Decision(title="B", summary="s")
    a.id = "abcdef1234"
    b.id = "abcdef5678"
    state.append_decision(a)
    state.append_decision(b)
    assert find_decision(state, "abcdef") is None
    # But the full id still resolves uniquely
    assert find_decision(state, "abcdef1234").title == "A"
    print("OK find_decision returns None on ambiguous prefix")


def test_studio_ratify_decision_tool_validates() -> None:
    state, _ = _fresh_studio()
    d = state.append_decision(Decision(title="X", summary="s", status=DecisionStatus.PROPOSED))

    # Unknown status
    r = studio_ratify_decision(d.id, "weird")
    assert r["ok"] is False
    assert "Unknown status" in r["error"]

    # Cannot ratify to PROPOSED
    r = studio_ratify_decision(d.id, "proposed")
    assert r["ok"] is False
    assert "proposed" in r["error"].lower()

    # SUPERSEDED requires superseded_by
    r = studio_ratify_decision(d.id, "superseded")
    assert r["ok"] is False
    assert "superseded_by" in r["error"]

    # Unknown id
    r = studio_ratify_decision("no-such-id", "accepted")
    assert r["ok"] is False
    assert "not found" in r["error"]

    # Happy path
    r = studio_ratify_decision(d.id, "accepted")
    assert r["ok"] is True
    assert r["new_status"] == "accepted"
    assert r["previous_status"] == "proposed"
    print("OK studio_ratify_decision tool validates + happy path")


def test_studio_ratify_decision_works_via_id_prefix() -> None:
    state, _ = _fresh_studio()
    d = state.append_decision(Decision(title="X", summary="s", status=DecisionStatus.PROPOSED))
    # The tool uses find_decision which accepts prefixes
    r = studio_ratify_decision(d.id[:6], "rejected")
    assert r["ok"] is True
    assert r["new_status"] == "rejected"
    print("OK studio_ratify_decision accepts unique id prefix")


def test_ratify_in_critic_allowlist_only() -> None:
    """Producer must not ratify -- per Producer prompt, only Critic does."""
    assert "studio_ratify_decision" in CRITIC.tool_set
    assert "studio_ratify_decision" not in PRODUCER.tool_set
    assert "studio_ratify_decision" not in DESIGNER.tool_set
    print("OK studio_ratify_decision in CRITIC only")


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
    test_latest_decisions_dedupes_by_id()
    test_ratify_unknown_id_returns_none()
    test_ratify_accept_appends_new_row_with_new_status()
    test_ratify_reject_path()
    test_ratify_supersede_links_to_replacement()
    test_query_decisions_reflects_ratified_status()
    test_decisions_summary_counts_latest_only()
    test_find_decision_by_exact_id_and_prefix()
    test_find_decision_returns_none_on_ambiguous_prefix()
    test_studio_ratify_decision_tool_validates()
    test_studio_ratify_decision_works_via_id_prefix()
    test_ratify_in_critic_allowlist_only()
    print("All Phase 15 + 18 decisions tests passed")


if __name__ == "__main__":
    run_test()
