"""P3 quality loop: assess_qa (pure) + unity_quality_pass (build->QA->fix)."""
import unitytools.tools.unity_tools as ut
from unitytools.core.quality import assess_qa


# --- assess_qa (pure) ------------------------------------------------------

def test_clean_scene_passes():
    a = assess_qa({"counts": {"renderers": 4, "lights": 2, "cameras": 1, "objects": 6}})
    assert a["passed"] is True
    assert a["fixes"] == []
    assert a["score"] == 100


def test_broken_materials_suggest_repair_first():
    a = assess_qa({"counts": {"renderers": 4, "lights": 2, "broken_materials": 2, "missing_materials": 1}})
    assert a["passed"] is False
    assert a["fixes"][0]["tool"] == "unity_repair_material_issues"
    assert a["fixes"][0]["params"]["include_unsupported"] is False
    assert a["score"] < 100


def test_unsupported_only_sets_include_flag():
    a = assess_qa({"counts": {"renderers": 2, "lights": 1, "unsupported_materials": 3}})
    assert a["fixes"][0]["tool"] == "unity_repair_material_issues"
    assert a["fixes"][0]["params"]["include_unsupported"] is True


def test_geometry_without_lights_suggests_lighting():
    a = assess_qa({"counts": {"renderers": 4, "lights": 0}})
    assert any(f["tool"] == "unity_setup_studio_lighting" for f in a["fixes"])
    assert a["passed"] is False


def test_empty_scene_is_noted_and_not_overfixed():
    a = assess_qa({"counts": {"renderers": 0, "lights": 0, "cameras": 0, "objects": 0}})
    assert "scene looks empty (no renderers)" in a["notes"]
    assert "no camera in scene" in a["notes"]
    # no renderers -> the "no lights" fix must NOT fire (nothing to light)
    assert a["fixes"] == []


def test_handles_none_and_empty():
    assert assess_qa(None)["fixes"] == []
    assert assess_qa({})["fixes"] == []
    # fix tools referenced must be real wrappers
    a = assess_qa({"counts": {"renderers": 1, "lights": 0, "broken_materials": 1}})
    for fx in a["fixes"]:
        assert hasattr(ut, fx["tool"]), fx["tool"]


# --- unity_quality_pass (the loop) -----------------------------------------

class _QABridge:
    """Returns broken materials on the 1st run_visual_qa, clean afterwards."""

    def __init__(self):
        self.calls = []
        self._qa = 0

    def call(self, method, params, timeout=None):
        self.calls.append((method, params))
        if method == "run_visual_qa":
            self._qa += 1
            broken = 3 if self._qa == 1 else 0
            return {
                "ok": True,
                "counts": {
                    "renderers": 5, "lights": 2, "cameras": 1, "objects": 7,
                    "missing_materials": 0, "broken_materials": broken,
                    "unsupported_materials": 0,
                },
                "issues": ([f"{broken} broken materials"] if broken else []),
                "verdict": ("issues" if broken else "ok"),
            }
        return {"ok": True}


def test_quality_pass_autofixes_then_passes(monkeypatch):
    fb = _QABridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_quality_pass(auto_fix=True, max_passes=3, capture_screenshot=False)
    assert r["ok"] is True
    assert r["passed"] is True
    methods = [m for (m, _p) in fb.calls]
    # snapshot before the repair, repair runs, QA runs at least twice (before+after)
    assert "create_scene_snapshot" in methods
    assert "repair_material_issues" in methods
    assert methods.count("run_visual_qa") >= 2
    assert methods.index("create_scene_snapshot") < methods.index("repair_material_issues")
    assert any(f["tool"] == "unity_repair_material_issues" for f in r["applied_fixes"])


def test_quality_pass_report_only_does_not_mutate(monkeypatch):
    fb = _QABridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_quality_pass(auto_fix=False, capture_screenshot=False)
    assert r["ok"] is True
    assert r["passed"] is False
    methods = [m for (m, _p) in fb.calls]
    assert "repair_material_issues" not in methods
    assert "create_scene_snapshot" not in methods
    assert methods.count("run_visual_qa") == 1


def test_quality_pass_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_quality_pass()["ok"] is False
