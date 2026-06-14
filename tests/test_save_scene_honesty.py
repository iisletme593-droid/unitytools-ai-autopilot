"""P4: unity_save_scene must honor the editor's result, not always report ok=true."""
import unitytools.tools.unity_tools as ut


class _FakeBridge:
    def __init__(self, result):
        self.result = result

    def call(self, method, params=None):
        return self.result


def test_save_scene_reports_failure(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", _FakeBridge({"ok": False, "path": "Assets/X.unity"}))
    r = ut.unity_save_scene()
    assert r["ok"] is False  # no longer a silent ok=true lie
    assert "error" in r


def test_save_scene_reports_success(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", _FakeBridge({"ok": True, "path": "Assets/Main.unity"}))
    r = ut.unity_save_scene()
    assert r["ok"] is True
    assert r["path"] == "Assets/Main.unity"


def test_save_scene_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_save_scene()["ok"] is False
