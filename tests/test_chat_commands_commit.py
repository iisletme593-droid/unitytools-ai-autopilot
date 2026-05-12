"""Phase 79 tests: /commit — git add+commit + journal entry.

/commit is the one slash command that shells out to git, so its tests
need to stand up isolated git repos in tmpdir and verify:
- Happy path: stage + commit + journal entry written with sha.
- Empty backlog of changes: clean 'nothing to commit' error.
- Not a git repo: clean 'not inside a git repo' error.
- Empty message: usage hint.
- Türkçe alias (/kaydet) routes to /commit.

Tests use git user.name + user.email scoped to the temp repo so they
don't depend on (or pollute) the host's global git config.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.cli.chat_commands import dispatch
from unitytools.studio import StudioPaths, StudioState, init_studio_tools


def _fresh_studio_in_git_repo() -> tuple[StudioState, Path, str]:
    """Make a tmpdir, `git init` it, scaffold a studio inside it, cd in.
    Returns (state, project_root, prev_cwd)."""
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="ph79-commit-"))
    project = tmp / "project"
    project.mkdir()
    paths = StudioPaths(project_root=project)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    # Init the git repo and pin a local identity
    subprocess.run(["git", "init", "-q"], cwd=str(project), check=True)
    subprocess.run(["git", "config", "user.email", "phase79@test.local"],
                    cwd=str(project), check=True)
    subprocess.run(["git", "config", "user.name", "Phase79Test"],
                    cwd=str(project), check=True)
    # Disable signing in case host has commit.gpgsign=true globally
    subprocess.run(["git", "config", "commit.gpgsign", "false"],
                    cwd=str(project), check=True)
    os.chdir(project)
    return state, project, prev


def _fresh_studio_no_git() -> tuple[StudioState, Path, str]:
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="ph79-nogit-"))
    project = tmp / "project"
    project.mkdir()
    paths = StudioPaths(project_root=project)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    state = StudioState(paths)
    init_studio_tools(state)
    os.chdir(project)
    return state, project, prev


# ─────────────────────────────────────── happy path


def test_commit_creates_real_git_commit() -> None:
    state, project, prev = _fresh_studio_in_git_repo()
    try:
        # Stage a real change
        state.paths.gdd.write_text("# GDD\nNew content\n", encoding="utf-8")
        r = dispatch("commit add GDD content")
        assert r.handled is True
        assert r.ok is True
        assert r.tool_name == "studio_commit"
        sha = r.tool_result["sha"]
        assert sha and sha != "?"
        # Verify the commit exists in git
        log = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=str(project), capture_output=True, text=True, encoding="utf-8",
        )
        assert sha in log.stdout, (
            f"git log should show {sha}; got {log.stdout!r}"
        )
        assert "add GDD content" in log.stdout
    finally:
        os.chdir(prev)
    print("OK /commit creates a real git commit with the supplied message")


def test_commit_writes_journal_entry_with_sha() -> None:
    state, project, prev = _fresh_studio_in_git_repo()
    try:
        state.paths.gdd.write_text("# GDD update", encoding="utf-8")
        r = dispatch("commit GDD update")
        sha = r.tool_result["sha"]
        # Today's journal should now contain the commit line
        today = time.strftime("%Y-%m-%d")
        jpath = state.paths.journal_for_date(today)
        assert jpath.is_file(), "journal entry not written"
        content = jpath.read_text(encoding="utf-8")
        assert sha in content
        assert "GDD update" in content
        assert content.startswith("# Journal —")
    finally:
        os.chdir(prev)
    print("OK /commit also appends 'commit <sha>: <msg>' to today's journal")


def test_commit_multi_word_message_joined() -> None:
    """Multi-word commit messages don't need quoting."""
    state, project, prev = _fresh_studio_in_git_repo()
    try:
        state.paths.gdd.write_text("# X", encoding="utf-8")
        r = dispatch("commit fix boss arena lighting bake")
        assert r.ok is True
        log = subprocess.run(
            ["git", "log", "--format=%s", "-1"],
            cwd=str(project), capture_output=True, text=True, encoding="utf-8",
        )
        assert log.stdout.strip() == "fix boss arena lighting bake"
    finally:
        os.chdir(prev)
    print("OK /commit joins multi-word args into one git message")


# ─────────────────────────────────────── error paths


def test_commit_nothing_to_commit_clean_error() -> None:
    state, project, prev = _fresh_studio_in_git_repo()
    try:
        # No changes staged
        r = dispatch("commit no changes here")
        assert r.handled is True
        assert r.ok is False
        assert "nothing to commit" in r.message.lower()
        # Journal NOT written
        today = time.strftime("%Y-%m-%d")
        jpath = state.paths.journal_for_date(today)
        # Either the file doesn't exist or it doesn't mention this msg
        if jpath.is_file():
            assert "no changes here" not in jpath.read_text(encoding="utf-8")
    finally:
        os.chdir(prev)
    print("OK /commit with nothing staged → clean 'nothing to commit' error")


def test_commit_outside_git_repo_fails_clean() -> None:
    state, project, prev = _fresh_studio_no_git()
    try:
        r = dispatch("commit anything")
        assert r.handled is True
        assert r.ok is False
        assert "not inside a git repo" in r.message.lower()
    finally:
        os.chdir(prev)
    print("OK /commit outside a git repo → clean 'not inside a git repo' error")


def test_commit_empty_message_returns_usage() -> None:
    state, project, prev = _fresh_studio_in_git_repo()
    try:
        r = dispatch("commit")
        assert r.handled is True
        assert r.ok is False
        assert "Usage" in r.message
        assert "/commit" in r.message
    finally:
        os.chdir(prev)
    print("OK /commit with no message → usage hint")


# ─────────────────────────────────────── alias parity


def test_commit_turkish_alias_kaydet() -> None:
    state, project, prev = _fresh_studio_in_git_repo()
    try:
        state.paths.gdd.write_text("# Türkçe alias test", encoding="utf-8")
        r = dispatch("kaydet türkçe commit mesajı")
        assert r.handled is True
        assert r.tool_name == "studio_commit"
        assert r.ok is True
        # Confirm it actually committed
        log = subprocess.run(
            ["git", "log", "--format=%s", "-1"],
            cwd=str(project), capture_output=True, text=True, encoding="utf-8",
        )
        assert "türkçe commit mesajı" in log.stdout
    finally:
        os.chdir(prev)
    print("OK /kaydet (Türkçe) → /commit, creates real git commit")


def test_help_lists_commit() -> None:
    r = dispatch("help")
    assert "/commit" in r.message, "/help should advertise /commit"
    print("OK /help advertises /commit")


def run_test() -> None:
    test_commit_creates_real_git_commit()
    test_commit_writes_journal_entry_with_sha()
    test_commit_multi_word_message_joined()
    test_commit_nothing_to_commit_clean_error()
    test_commit_outside_git_repo_fails_clean()
    test_commit_empty_message_returns_usage()
    test_commit_turkish_alias_kaydet()
    test_help_lists_commit()
    print("All Phase 79 /commit tests passed")


if __name__ == "__main__":
    run_test()
