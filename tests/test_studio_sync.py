"""Phase 63 tests: studio_sync.

Studio schema evolves with each UnityTools release (more starter
docs, more directories). studio_sync brings an existing scaffold
up to current schema without overwriting user content.

Also tests auto-sync-on-chat-start path: opening chat in a stale
studio should silently migrate it.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.cli.chat_commands import dispatch
from unitytools.studio import PRODUCER, StudioPaths, StudioState, init_studio_tools
from unitytools.studio.tools import studio_sync


def _stale_studio() -> tuple[StudioState, Path, str]:
    """Build a 'stale' studio that lacks several of the newer
    canonical docs + directories. Returns the state, the project
    root, and the previous cwd."""
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="stale-studio-"))
    paths = StudioPaths(project_root=tmp)
    # Create only the original Phase 2-ish directories + 3 base docs;
    # leave out Phase 47+ docs (tutorial, scene_catalog, achievements,
    # press_kit) and Phase 39/55 dirs (strings/, dialogs/).
    legacy_dirs = [paths.root, paths.refs, paths.reviews, paths.qa,
                    paths.qa_screenshots, paths.memory, paths.archive_root]
    for d in legacy_dirs:
        d.mkdir(parents=True, exist_ok=True)
    paths.gdd.write_text("# Original GDD\nUser content.\n", encoding="utf-8")
    paths.art_bible.write_text("# Original Art Bible\n", encoding="utf-8")
    paths.audio_brief.write_text("# Original Audio Brief\n", encoding="utf-8")
    state = StudioState(paths)
    init_studio_tools(state)
    os.chdir(tmp)
    return state, tmp, prev


def _current_studio() -> tuple[StudioState, Path, str]:
    """Build a current-schema studio (every docs + dirs in place)."""
    from unitytools.studio.templates import starter_files
    prev = os.getcwd()
    tmp = Path(tempfile.mkdtemp(prefix="current-studio-"))
    paths = StudioPaths(project_root=tmp)
    for d in paths.all_dirs():
        d.mkdir(parents=True, exist_ok=True)
    for rel, content in starter_files().items():
        target = paths.root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    state = StudioState(paths)
    init_studio_tools(state)
    os.chdir(tmp)
    return state, tmp, prev


# ─────────────────────────────────────────── check-only mode


def test_sync_check_only_reports_drift_without_writing() -> None:
    state, tmp, prev = _stale_studio()
    try:
        r = studio_sync(check_only=True)
        assert r["ok"] is True
        assert r["in_sync"] is False
        assert r["drift_count"] >= 5, (
            f"stale studio should have several drift items; got {r['drift_count']}"
        )
        # Missing newer docs
        for expected in ("press_kit.md", "tutorial.md", "scene_catalog.md",
                          "achievements.md", "sprint_current.md"):
            assert expected in r["missing_files"], f"check should flag {expected}"
        # The missing dirs were NOT created (check-only)
        assert not (tmp / "studio" / "strings").exists()
        assert not (tmp / "studio" / "dialogs").exists()
        # No actions in check-only
        assert r["actions_applied"] == []
    finally:
        os.chdir(prev)
    print("OK /sync --check reports drift items, never writes")


def test_sync_check_only_on_current_studio_reports_in_sync() -> None:
    state, tmp, prev = _current_studio()
    try:
        r = studio_sync(check_only=True)
        assert r["in_sync"] is True
        assert r["drift_count"] == 0
        assert r["missing_files"] == []
        assert r["missing_dirs"] == []
    finally:
        os.chdir(prev)
    print("OK current-schema studio reports in_sync=True with 0 drift")


# ─────────────────────────────────────────── apply migrations


def test_sync_applies_migrations_creating_missing_dirs_and_files() -> None:
    state, tmp, prev = _stale_studio()
    try:
        before = studio_sync(check_only=True)
        drift_before = before["drift_count"]
        # Apply
        r = studio_sync(check_only=False)
        assert r["ok"] is True
        assert len(r["actions_applied"]) == drift_before, (
            f"actions_applied count should match check-only drift; "
            f"got {len(r['actions_applied'])} vs drift={drift_before}"
        )
        # Now every newer doc + dir exists
        from unitytools.studio.templates import starter_files
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=tmp)
        for rel in starter_files().keys():
            assert (paths.root / rel).exists(), f"sync should have created {rel}"
        for d in paths.all_dirs():
            assert d.is_dir(), f"sync should have created dir {d}"
    finally:
        os.chdir(prev)
    print(f"OK /sync (apply) creates every missing file + dir")


def test_sync_preserves_existing_user_content() -> None:
    """Critical: sync must NEVER overwrite a file that already
    exists. The user's GDD content survives migration."""
    state, tmp, prev = _stale_studio()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=tmp)
        original_gdd = paths.gdd.read_text(encoding="utf-8")
        original_ab = paths.art_bible.read_text(encoding="utf-8")
        # Apply migrations
        studio_sync(check_only=False)
        # User content untouched
        assert paths.gdd.read_text(encoding="utf-8") == original_gdd
        assert paths.art_bible.read_text(encoding="utf-8") == original_ab
        assert "User content" in paths.gdd.read_text(encoding="utf-8")
    finally:
        os.chdir(prev)
    print("OK pre-existing user content (GDD, Art Bible) preserved through sync")


def test_sync_is_idempotent() -> None:
    """Running sync twice on the same studio should be safe and
    the second run reports in_sync."""
    state, tmp, prev = _stale_studio()
    try:
        studio_sync(check_only=False)
        r = studio_sync(check_only=False)
        assert r["in_sync"] is True
        assert r["drift_count"] == 0
        assert r["actions_applied"] == []
    finally:
        os.chdir(prev)
    print("OK /sync is idempotent — second run is a no-op")


# ─────────────────────────────────────────── /sync slash command


def test_sync_slash_command_recognised() -> None:
    state, tmp, prev = _stale_studio()
    try:
        r = dispatch("sync")
        assert r.handled is True
        assert r.tool_name == "studio_sync"
    finally:
        os.chdir(prev)
    print("OK /sync slash command recognised")


def test_sync_slash_command_check_flag() -> None:
    """`/sync --check` should NOT write."""
    state, tmp, prev = _stale_studio()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=tmp)
        before_exists = (paths.root / "tutorial.md").exists()
        assert before_exists is False
        r = dispatch("sync --check")
        assert r.handled is True
        assert r.tool_result["check_only"] is True
        # tutorial.md was NOT created
        assert not (paths.root / "tutorial.md").exists()
    finally:
        os.chdir(prev)
    print("OK /sync --check is read-only (doesn't create files)")


def test_sync_slash_command_apply() -> None:
    """`/sync` (no flag) actually applies migrations."""
    state, tmp, prev = _stale_studio()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=tmp)
        r = dispatch("sync")
        assert r.handled is True
        assert r.tool_result["check_only"] is False
        # Now newer docs exist
        assert (paths.root / "tutorial.md").exists()
        assert (paths.root / "scene_catalog.md").exists()
        assert (paths.root / "achievements.md").exists()
    finally:
        os.chdir(prev)
    print("OK /sync applies migrations end-to-end")


# ─────────────────────────────────────────── auto-sync on chat start


def test_auto_sync_runs_when_chat_starts_on_stale_studio() -> None:
    """The killer feature: opening chat in a stale studio
    silently migrates it. The user never has to think about
    schema drift."""
    from unitytools.cli.chat import _init_studio_for_chat
    state, tmp, prev = _stale_studio()
    try:
        from unitytools.studio import StudioPaths
        paths = StudioPaths(project_root=tmp)
        # Pre-condition: tutorial.md doesn't exist
        assert not (paths.root / "tutorial.md").exists()

        class FakeBridge:
            def is_connected(self): return False
            def connect(self, *a, **k): return False
            def call(self, *a, **k): raise NotImplementedError

        active, info = _init_studio_for_chat(FakeBridge())
        assert active is True
        # The info string mentions schema migrations were applied
        assert "schema migrations" in info, f"expected migration count in info; got {info!r}"
        # Post-condition: tutorial.md now exists
        assert (paths.root / "tutorial.md").exists()
        assert (paths.root / "scene_catalog.md").exists()
        # User content still intact
        assert "User content" in paths.gdd.read_text(encoding="utf-8")
    finally:
        os.chdir(prev)
    print("OK auto-sync runs silently when chat opens a stale studio (no manual /sync needed)")


def test_auto_sync_silent_on_current_studio() -> None:
    """When studio is already current, the welcome banner shouldn't
    mention sync — there was nothing to do."""
    from unitytools.cli.chat import _init_studio_for_chat
    state, tmp, prev = _current_studio()
    try:
        class FakeBridge:
            def is_connected(self): return False
            def connect(self, *a, **k): return False
            def call(self, *a, **k): raise NotImplementedError

        active, info = _init_studio_for_chat(FakeBridge())
        assert active is True
        assert "schema migrations" not in info, (
            "current-schema studio should not show migration count"
        )
    finally:
        os.chdir(prev)
    print("OK current-schema studio: chat banner doesn't claim a migration ran")


# ─────────────────────────────────────────── role surface


def test_producer_has_sync_tool() -> None:
    """Producer cites schema drift in standup + can run sync to clear it."""
    assert "studio_sync" in PRODUCER.tool_set
    print("OK Producer has studio_sync in its allowlist")


def run_test() -> None:
    # Check-only mode
    test_sync_check_only_reports_drift_without_writing()
    test_sync_check_only_on_current_studio_reports_in_sync()
    # Apply mode
    test_sync_applies_migrations_creating_missing_dirs_and_files()
    test_sync_preserves_existing_user_content()
    test_sync_is_idempotent()
    # Slash command
    test_sync_slash_command_recognised()
    test_sync_slash_command_check_flag()
    test_sync_slash_command_apply()
    # Auto-sync
    test_auto_sync_runs_when_chat_starts_on_stale_studio()
    test_auto_sync_silent_on_current_studio()
    # Role surface
    test_producer_has_sync_tool()
    print("All Phase 63 studio_sync tests passed")


if __name__ == "__main__":
    run_test()
