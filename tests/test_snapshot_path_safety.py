"""P4 security (cycle 13): unity_restore_scene_snapshot path-traversal guard.

The model picks the snapshot path, so it is confined to Assets/ and absolute /
drive-letter / '..'-escaping paths are rejected BEFORE the bridge opens it. Also
covers core.security.safe_contained_path itself (untested before).
"""
import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.security import safe_contained_path


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params, timeout=None):
        self.calls.append((method, params))
        return {"ok": True}


def test_legit_snapshot_path_passes(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_restore_scene_snapshot("Assets/AutopilotSnapshots/Main_20260614_manual.unity")
    assert r["ok"] is True
    assert fb.calls[0][0] == "restore_scene_snapshot"
    assert fb.calls[0][1]["path"] == "Assets/AutopilotSnapshots/Main_20260614_manual.unity"


@pytest.mark.parametrize("bad", [
    "Assets/../../etc/passwd",       # traversal escape
    "Assets\\..\\..\\secret.unity",  # backslash traversal
    "/etc/passwd",                   # absolute, not under Assets
    "C:/Windows/system32",           # drive-letter
    "Library/cache.unity",           # outside Assets
    "",                              # empty
])
def test_unsafe_paths_rejected_without_calling_bridge(monkeypatch, bad):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_restore_scene_snapshot(bad)
    assert r["ok"] is False
    assert fb.calls == []   # the bridge is never asked to open it


def test_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_restore_scene_snapshot("Assets/x.unity")["ok"] is False


# --- safe_contained_path itself --------------------------------------------

def test_safe_contained_path_allows_contained():
    p = safe_contained_path("Assets", "AutopilotSnapshots/x.unity")
    assert str(p).replace("\\", "/").endswith("Assets/AutopilotSnapshots/x.unity")


@pytest.mark.parametrize("rel", ["../../etc/passwd", "/etc/passwd", "C:/Windows", ""])
def test_safe_contained_path_rejects(rel):
    with pytest.raises(ValueError):
        safe_contained_path("Assets", rel)
