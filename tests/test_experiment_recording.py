"""P3 (cycle 5): close the build->measure->learn loop.

metrics_from_signals derives measurable metrics from visual-QA + profiling, and
gamestudio_record_scene_experiment auto-records them — so experiments carry real
numbers instead of the always-None operator-typed metrics the scan flagged.
"""
import json

import unitytools.tools.unity_tools as ut
import unitytools.tools.game_studio_tools as gst
from unitytools.core.game_studio_kernel import GameStudioKernel
from unitytools.core.quality import metrics_from_signals


# --- pure derivation -------------------------------------------------------

def test_clean_scene_high_clarity_good_fps():
    qa = {"ok": True, "verdict": "QA passed",
          "counts": {"renderers": 10, "lights": 2, "cameras": 1, "objects": 12,
                     "missing_materials": 0, "broken_materials": 0, "unsupported_materials": 0}}
    profile = {"ok": True, "triangles": 500_000, "suggestions": []}
    d = metrics_from_signals(qa, profile)
    assert d["metrics"]["clarity_score"] == 10.0
    assert d["metrics"]["fps_average"] == 60        # 500k < 1M budget -> full
    assert d["metrics"]["crash_count"] == 0
    assert d["metrics"]["fun_score"] is None        # not measurable
    assert d["outcome"] == "promising"


def test_broken_materials_lower_clarity():
    qa = {"ok": True, "counts": {"renderers": 5, "lights": 1, "cameras": 1, "broken_materials": 3}}
    d = metrics_from_signals(qa, {"triangles": 100})
    assert d["metrics"]["clarity_score"] == 4.0     # 10 - 2*3
    assert d["outcome"] in ("mixed", "needs_work")


def test_high_triangles_low_fps_proxy():
    d = metrics_from_signals({"ok": True, "counts": {"renderers": 1, "lights": 1, "cameras": 1}},
                             {"triangles": 4_000_000})
    assert d["metrics"]["fps_average"] == 15        # 60 * 1M/4M
    assert d["outcome"] == "needs_work"


def test_no_lights_penalizes_clarity():
    d = metrics_from_signals({"counts": {"renderers": 8, "lights": 0, "cameras": 1}}, {})
    assert d["metrics"]["clarity_score"] == 8.0     # -2 for geometry w/o lights
    assert d["metrics"]["fps_average"] is None      # no triangle data


def test_handles_empty():
    d = metrics_from_signals(None, None)
    assert d["metrics"]["fps_average"] is None
    assert d["metrics"]["clarity_score"] == 9.0     # only the "no camera" -1 applies


# --- the tool (auto-record) ------------------------------------------------

class _SceneBridge:
    def call(self, method, params=None, timeout=None):
        if method == "run_visual_qa":
            return {"ok": True, "verdict": "QA passed",
                    "counts": {"renderers": 10, "lights": 2, "cameras": 1, "objects": 12,
                               "missing_materials": 0, "broken_materials": 0, "unsupported_materials": 0}}
        if method == "profile_scene_performance":
            return {"ok": True, "triangles": 500_000, "vertices": 300_000, "suggestions": ["combine static meshes"]}
        return {"ok": True}

    def is_connected(self):
        return True


def test_record_scene_experiment_writes_measured_metrics(tmp_path, monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", _SceneBridge())
    monkeypatch.setattr(gst, "GameStudioKernel",
                        lambda workspace="GameStudioData": GameStudioKernel(root=tmp_path, workspace=workspace))

    r = gst.gamestudio_record_scene_experiment(game_title="forest_v1", hypothesis="denser canopy")
    assert r["ok"] is True
    assert r["metrics"]["clarity_score"] == 10.0
    assert r["metrics"]["fps_average"] == 60
    assert r["outcome"] == "promising"

    # the experiment was actually persisted to the studio memory
    exp_file = tmp_path / "GameStudioData" / "experiments.jsonl"
    assert exp_file.exists()
    rows = [json.loads(l) for l in exp_file.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert rows[-1]["game_title"] == "forest_v1"
    assert rows[-1]["metrics"]["clarity_score"] == 10.0


def test_record_scene_experiment_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    r = gst.gamestudio_record_scene_experiment(game_title="x")
    assert r["ok"] is False
