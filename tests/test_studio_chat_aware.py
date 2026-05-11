"""Phase 56 tests: studio-aware chat REPL.

The chat REPL `_init_studio_for_chat` must:
- Discover a studio/ directory by walking up from CWD
- Match only studio/ folders with the canonical markers
  (gdd.md / backlog.json / decisions.jsonl / art_bible.md /
  sprint_current.md), not random 'studio' folders
- Init StudioState + Unity bridge when found
- Fail gracefully when no studio is around (chat still launches)
- Eagerly import unitytools.tools.* so the @tool registry has
  every wrapper
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from unitytools.cli.chat import _discover_studio_root, _init_studio_for_chat


class FakeBridge:
    """Minimal UnityBridge stand-in that init_studio_unity will accept."""

    def is_connected(self):
        return False

    def call(self, method, params=None, timeout=None):
        raise AssertionError("FakeBridge should not be called during init")


# ───────────────────────────────────────────── discover


def test_discover_returns_none_when_no_studio_anywhere() -> None:
    """In a fresh temp dir with no studio/ sibling, discovery fails
    cleanly."""
    with tempfile.TemporaryDirectory() as tmp:
        result = _discover_studio_root(Path(tmp))
        assert result is None
    print("OK no studio/ anywhere -> _discover_studio_root returns None")


def test_discover_matches_studio_with_canonical_marker() -> None:
    """A studio/ folder with gdd.md inside should be discovered."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        studio = root / "studio"
        studio.mkdir()
        (studio / "gdd.md").write_text("# GDD", encoding="utf-8")
        result = _discover_studio_root(root)
        assert result == root.resolve()
    print("OK studio/ with gdd.md is discovered")


def test_discover_walks_up_from_subdirectory() -> None:
    """Discovery should walk UP from cwd, not just check cwd itself."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        studio = root / "studio"
        studio.mkdir()
        (studio / "art_bible.md").write_text("# AB", encoding="utf-8")
        deep = root / "src" / "nested" / "deeply"
        deep.mkdir(parents=True)
        result = _discover_studio_root(deep)
        assert result == root.resolve()
    print("OK discovery walks up from a deep subdirectory")


def test_discover_rejects_unrelated_studio_folder() -> None:
    """A 'studio' folder without any of the canonical markers should
    NOT match — otherwise a random /home/me/studio/ would hijack
    every chat session."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # An empty studio/ with nothing canonical inside
        (root / "studio").mkdir()
        (root / "studio" / "random.txt").write_text("not us", encoding="utf-8")
        result = _discover_studio_root(root)
        assert result is None
    print("OK empty 'studio' folder without canonical markers is rejected")


def test_discover_accepts_each_canonical_marker() -> None:
    """Any one of the 5 canonical markers is enough to confirm match."""
    markers = ("gdd.md", "backlog.json", "decisions.jsonl",
                "art_bible.md", "sprint_current.md")
    for m in markers:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "studio").mkdir()
            (root / "studio" / m).write_text("x", encoding="utf-8")
            result = _discover_studio_root(root)
            assert result == root.resolve(), f"marker {m!r} should have qualified"
    print(f"OK each of the 5 canonical markers ({markers}) qualifies the folder")


# ───────────────────────────────────────────── init


def test_init_returns_inactive_when_no_studio_present() -> None:
    """No studio nearby: returns (False, reason) but doesn't crash —
    chat should still launch."""
    cwd_was = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            active, info = _init_studio_for_chat(FakeBridge())
            assert active is False
            assert "no studio" in info.lower() or "not" in info.lower()
        finally:
            os.chdir(cwd_was)
    print("OK no studio nearby -> _init returns (False, reason) without crashing")


def test_init_returns_active_with_real_studio() -> None:
    """A real scaffolded studio should be picked up."""
    from unitytools.studio import StudioPaths, StudioState
    cwd_was = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = StudioPaths(project_root=root)
        for d in paths.all_dirs():
            d.mkdir(parents=True, exist_ok=True)
        # Seed at least one canonical marker
        paths.gdd.write_text("# GDD", encoding="utf-8")
        os.chdir(root)
        try:
            active, info = _init_studio_for_chat(FakeBridge())
            assert active is True, f"expected studio active; got info={info!r}"
            assert str(root.resolve()) in info or str(root) in info
        finally:
            os.chdir(cwd_was)
    print("OK real scaffolded studio is picked up; state + bridge wired")


def test_init_eagerly_imports_engine_tool_modules() -> None:
    """After _init, the @tool registry should include unity_* tools
    (registered as a side effect of importing the tool modules)."""
    from unitytools.core.tool_registry import get_all_tools
    with tempfile.TemporaryDirectory() as tmp:
        cwd_was = os.getcwd()
        os.chdir(tmp)
        try:
            _init_studio_for_chat(FakeBridge())
        finally:
            os.chdir(cwd_was)
    tool_names = {t.name for t in get_all_tools()}
    # Spot-check a few unity_* tools we know exist
    assert "unity_create_primitive" in tool_names, (
        "unity_* tools should be in the @tool registry after chat init "
        "so the LLM can call them"
    )
    assert "unity_attach_behaviour" in tool_names
    print(f"OK engine tool modules eagerly imported; {len(tool_names)} tools registered")


# ─────────────────────────────────────────── Phase 62 auto-scaffold


def test_discover_unity_project_root_finds_assets_plus_settings() -> None:
    """A directory with BOTH Assets/ and ProjectSettings/ qualifies
    as a Unity project root."""
    from unitytools.cli.chat import _discover_unity_project_root
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Assets").mkdir()
        (root / "ProjectSettings").mkdir()
        result = _discover_unity_project_root(root)
        assert result == root.resolve()
    print("OK Unity project (Assets/ + ProjectSettings/) is detected")


def test_discover_unity_project_root_walks_up() -> None:
    """Running chat from a subdirectory of a Unity project should
    still find the project root."""
    from unitytools.cli.chat import _discover_unity_project_root
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Assets").mkdir()
        (root / "ProjectSettings").mkdir()
        deep = root / "Assets" / "Scripts" / "Player"
        deep.mkdir(parents=True)
        result = _discover_unity_project_root(deep)
        assert result == root.resolve()
    print("OK Unity project root discovered by walking up from a subdirectory")


def test_discover_unity_rejects_assets_without_settings() -> None:
    """A folder named 'Assets' alone (e.g. some random art portfolio)
    is NOT a Unity project. Need both Assets/ AND ProjectSettings/."""
    from unitytools.cli.chat import _discover_unity_project_root
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Assets").mkdir()
        # NO ProjectSettings/
        result = _discover_unity_project_root(root)
        assert result is None
    print("OK Assets/ alone (no ProjectSettings/) is NOT detected as Unity project")


def test_auto_scaffold_when_chat_starts_in_unity_project() -> None:
    """The whole point of Phase 62: open chat in a Unity project,
    no studio/ yet, studio gets auto-created."""
    from unitytools.cli.chat import _init_studio_for_chat
    cwd_was = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Assets").mkdir()
        (root / "ProjectSettings").mkdir()
        os.chdir(root)
        try:
            active, info = _init_studio_for_chat(FakeBridge())
            assert active is True, f"expected active studio; info={info}"
            assert "auto-scaffolded" in info, (
                f"expected auto-scaffolded marker in info string; got {info!r}"
            )
            # The studio/ dir + canonical docs exist
            assert (root / "studio").is_dir()
            for doc in ("gdd.md", "art_bible.md", "audio_brief.md",
                         "press_kit.md", "tutorial.md",
                         "scene_catalog.md", "achievements.md",
                         "sprint_current.md"):
                assert (root / "studio" / doc).exists(), f"missing {doc}"
        finally:
            os.chdir(cwd_was)
    print("OK chat in Unity project w/o studio -> auto-scaffolds all 8 starter docs")


def test_auto_scaffold_disabled_when_opted_out() -> None:
    """--no-auto-init / auto_scaffold=False: the chat still launches,
    but studio_* tools won't work until the user runs /init."""
    from unitytools.cli.chat import _init_studio_for_chat
    cwd_was = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Assets").mkdir()
        (root / "ProjectSettings").mkdir()
        os.chdir(root)
        try:
            active, info = _init_studio_for_chat(FakeBridge(), auto_scaffold=False)
            assert active is False
            assert "no studio" in info.lower()
            assert not (root / "studio").exists(), (
                "auto_scaffold=False should NOT create studio/"
            )
        finally:
            os.chdir(cwd_was)
    print("OK auto_scaffold=False respects the opt-out (no studio/ created)")


def test_no_auto_scaffold_outside_unity_project() -> None:
    """In a directory that doesn't look like a Unity project, do NOT
    auto-create studio/. Otherwise we'd pollute random folders the
    user happens to `cd` into."""
    from unitytools.cli.chat import _init_studio_for_chat
    cwd_was = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # No Assets/, no ProjectSettings/
        os.chdir(root)
        try:
            active, info = _init_studio_for_chat(FakeBridge())
            assert active is False
            assert not (root / "studio").exists(), (
                "non-Unity dir should NOT get a studio/ scaffolded"
            )
            # Helpful error message points to /init or cd
            assert "/init" in info or "Unity project" in info
        finally:
            os.chdir(cwd_was)
    print("OK non-Unity directory: no studio auto-created (no pollution)")


def test_existing_studio_takes_priority_over_auto_scaffold() -> None:
    """If a studio/ already exists, use it as-is. Don't overwrite."""
    from unitytools.cli.chat import _init_studio_for_chat
    from unitytools.studio import StudioPaths, StudioState
    cwd_was = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "Assets").mkdir()
        (root / "ProjectSettings").mkdir()
        # Pre-populate a studio with a sentinel value
        paths = StudioPaths(project_root=root)
        for d in paths.all_dirs():
            d.mkdir(parents=True, exist_ok=True)
        paths.gdd.write_text("# Pre-existing GDD\nUser content.\n", encoding="utf-8")
        os.chdir(root)
        try:
            active, info = _init_studio_for_chat(FakeBridge())
            assert active is True
            # The "auto-scaffolded" marker should NOT be in info
            assert "auto-scaffolded" not in info, (
                "should NOT auto-scaffold over an existing studio"
            )
            # User content survives
            assert "User content" in paths.gdd.read_text(encoding="utf-8")
        finally:
            os.chdir(cwd_was)
    print("OK pre-existing studio/ takes priority — auto-scaffold doesn't overwrite")


def test_init_makes_studio_tools_callable_after_state_wire() -> None:
    """After init, calling a studio_* tool should NOT error with
    'state not initialized'."""
    from unitytools.studio import StudioPaths, StudioState
    from unitytools.studio.tools import studio_get_summary
    cwd_was = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = StudioPaths(project_root=root)
        for d in paths.all_dirs():
            d.mkdir(parents=True, exist_ok=True)
        paths.gdd.write_text("# GDD", encoding="utf-8")
        os.chdir(root)
        try:
            active, _ = _init_studio_for_chat(FakeBridge())
            assert active is True
            summary = studio_get_summary()
            assert summary["ok"] is True, f"studio_get_summary should work; got {summary}"
            assert summary["has_gdd"] is True
        finally:
            os.chdir(cwd_was)
    print("OK after _init, studio_get_summary works end-to-end (no 'state not initialized')")


def run_test() -> None:
    test_discover_returns_none_when_no_studio_anywhere()
    test_discover_matches_studio_with_canonical_marker()
    test_discover_walks_up_from_subdirectory()
    test_discover_rejects_unrelated_studio_folder()
    test_discover_accepts_each_canonical_marker()
    test_init_returns_inactive_when_no_studio_present()
    test_init_returns_active_with_real_studio()
    test_init_eagerly_imports_engine_tool_modules()
    test_init_makes_studio_tools_callable_after_state_wire()
    # Phase 62 auto-scaffold
    test_discover_unity_project_root_finds_assets_plus_settings()
    test_discover_unity_project_root_walks_up()
    test_discover_unity_rejects_assets_without_settings()
    test_auto_scaffold_when_chat_starts_in_unity_project()
    test_auto_scaffold_disabled_when_opted_out()
    test_no_auto_scaffold_outside_unity_project()
    test_existing_studio_takes_priority_over_auto_scaffold()
    print("All studio-aware chat tests passed (Phase 56 + 62)")


if __name__ == "__main__":
    run_test()
