"""Wired bridge tools: thin @tool wrappers over existing CommandHandlers commands
that previously had no Python tool (so the autopilot LLM could not call them).

Each test asserts the wrapper forwards to the correct bridge command with the
exact param keys the C# handler reads, and fails safe when the bridge is absent.
"""
import unitytools.tools.unity_tools as ut


class _FakeBridge:
    def __init__(self):
        self.calls = []

    def call(self, method, params, timeout=None):
        self.calls.append((method, params))
        return {"ok": True}


# --- materials -------------------------------------------------------------

def test_apply_material_palette_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_apply_material_palette(query="tree", category="foliage", palette="desert", max=500)
    assert r["ok"] is True
    assert fb.calls[0][0] == "apply_material_palette"
    assert fb.calls[0][1] == {"query": "tree", "category": "foliage", "palette": "desert", "max": 500}


def test_apply_material_palette_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_apply_material_palette()["ok"] is False


def test_diagnose_material_issues_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_diagnose_material_issues(query="rock", category="prop", max=1000)
    assert r["ok"] is True
    assert fb.calls[0][0] == "diagnose_material_issues"
    assert fb.calls[0][1] == {"query": "rock", "category": "prop", "max": 1000}


def test_diagnose_material_issues_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_diagnose_material_issues()["ok"] is False


def test_repair_material_issues_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_repair_material_issues(query="wall", category="building", tint=True, palette="desert", include_unsupported=True, max=300)
    assert r["ok"] is True
    assert fb.calls[0][0] == "repair_material_issues"
    assert fb.calls[0][1] == {"query": "wall", "category": "building", "tint": True, "palette": "desert", "include_unsupported": True, "max": 300}


def test_repair_material_issues_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_repair_material_issues()["ok"] is False


def test_repair_texture_import_settings_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_repair_texture_import_settings(query="t:Texture2D rock", max=200)
    assert r["ok"] is True
    assert fb.calls[0][0] == "repair_texture_import_settings"
    assert fb.calls[0][1] == {"query": "t:Texture2D rock", "max": 200}


def test_repair_texture_import_settings_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_repair_texture_import_settings()["ok"] is False


# --- scene generation / catalog -------------------------------------------

def test_create_optimized_forest_scene_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_create_optimized_forest_scene(clear_scene=False, tree_count=80, rock_count=10, terrain_size=200.0, seed=42)
    assert r["ok"] is True
    assert fb.calls[0][0] == "create_optimized_forest_scene"
    params = fb.calls[0][1]
    assert params["clear_scene"] is False
    assert params["tree_count"] == 80
    assert params["rock_count"] == 10
    assert params["terrain_size"] == 200.0
    assert params["seed"] == 42


def test_create_optimized_forest_scene_defaults(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_create_optimized_forest_scene()
    params = fb.calls[0][1]
    assert params == {"clear_scene": True, "tree_count": 100, "rock_count": 18, "terrain_size": 120.0, "seed": 12345}


def test_create_optimized_forest_scene_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_create_optimized_forest_scene()["ok"] is False


def test_get_scene_catalog_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_get_scene_catalog(max_results=250)
    assert r["ok"] is True
    assert fb.calls[0][0] == "get_scene_catalog"
    assert fb.calls[0][1] == {"max_results": 250}


def test_get_scene_catalog_default(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_get_scene_catalog()
    assert fb.calls[0][1] == {"max_results": 1000}


def test_get_scene_catalog_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_get_scene_catalog()["ok"] is False


# --- semantic find / delete ------------------------------------------------

def test_find_scene_objects_semantic_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_find_scene_objects_semantic(query="tree", category="vegetation", max_results=50)
    assert r["ok"] is True
    assert fb.calls[0][0] == "find_scene_objects_semantic"
    assert fb.calls[0][1] == {"query": "tree", "category": "vegetation", "max_results": 50}


def test_find_scene_objects_semantic_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_find_scene_objects_semantic(query="tree")["ok"] is False


def test_delete_scene_objects_semantic_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_delete_scene_objects_semantic(query="rock", category="prop", max=200)
    assert r["ok"] is True
    assert fb.calls[0][0] == "delete_scene_objects_semantic"
    # NOTE: the delete handler reads "max" (not "max_results") — guard against regressions
    assert fb.calls[0][1] == {"query": "rock", "category": "prop", "max": 200}


def test_delete_scene_objects_semantic_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_delete_scene_objects_semantic(query="rock")["ok"] is False


# --- visual QA / snapshots -------------------------------------------------

def test_run_visual_qa_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_run_visual_qa(capture_screenshot=False)
    assert r["ok"] is True
    assert fb.calls[0][0] == "run_visual_qa"
    assert fb.calls[0][1] == {"capture_screenshot": False}


def test_run_visual_qa_default_captures(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_run_visual_qa()
    assert fb.calls[0][1] == {"capture_screenshot": True}


def test_run_visual_qa_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_run_visual_qa()["ok"] is False


def test_create_scene_snapshot_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_create_scene_snapshot(label="before_blockout")
    assert r["ok"] is True
    assert fb.calls[0][0] == "create_scene_snapshot"
    assert fb.calls[0][1] == {"label": "before_blockout"}


def test_create_scene_snapshot_default_label(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_create_scene_snapshot()
    assert fb.calls[0][1] == {"label": "manual"}


def test_create_scene_snapshot_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_create_scene_snapshot()["ok"] is False


def test_restore_scene_snapshot_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_restore_scene_snapshot("Assets/AutopilotSnapshots/Main_20260614_120000_manual.unity")
    assert r["ok"] is True
    assert fb.calls[0][0] == "restore_scene_snapshot"
    assert fb.calls[0][1] == {"path": "Assets/AutopilotSnapshots/Main_20260614_120000_manual.unity"}


def test_restore_scene_snapshot_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_restore_scene_snapshot("Assets/AutopilotSnapshots/x.unity")["ok"] is False


# --- performance / LOD -----------------------------------------------------

def test_profile_scene_performance_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_profile_scene_performance(5000)
    assert r["ok"] is True
    assert fb.calls[0][0] == "profile_scene_performance"
    assert fb.calls[0][1] == {"max_objects": 5000}


def test_profile_scene_performance_default_param(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_profile_scene_performance()
    assert fb.calls[0][1] == {"max_objects": 10000}


def test_profile_scene_performance_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_profile_scene_performance(5000)["ok"] is False


def test_optimize_editor_performance_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_optimize_editor_performance(30.0, 0.4)
    assert r["ok"] is True
    assert fb.calls[0][0] == "optimize_editor_performance"
    assert fb.calls[0][1] == {"shadow_distance": 30.0, "lod_bias": 0.4}


def test_optimize_editor_performance_defaults(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_optimize_editor_performance()
    assert fb.calls[0][1] == {"shadow_distance": 25.0, "lod_bias": 0.55}


def test_optimize_editor_performance_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_optimize_editor_performance()["ok"] is False


def test_analyze_lod_decimation_candidates_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_analyze_lod_decimation_candidates("tree", "tree", 10, 50000)
    assert r["ok"] is True
    assert fb.calls[0][0] == "analyze_lod_decimation_candidates"
    assert fb.calls[0][1] == {"query": "tree", "category": "tree", "max_results": 10, "min_triangles": 50000}


def test_analyze_lod_decimation_candidates_defaults(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_analyze_lod_decimation_candidates()
    assert fb.calls[0][1] == {"query": "", "category": "", "max_results": 25, "min_triangles": 10000}


def test_analyze_lod_decimation_candidates_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_analyze_lod_decimation_candidates()["ok"] is False


def test_apply_lod_decimation_plan_calls_bridge(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    r = ut.unity_apply_lod_decimation_plan(
        query="pine", category="tree", max_objects=50, min_triangles_per_object=30000,
        create_proxy_lods=True, replace_with_proxy=True, disable_shadows=False,
        mark_static=False, lod0_screen_relative_height=0.4, lod1_screen_relative_height=0.1,
    )
    assert r["ok"] is True
    assert fb.calls[0][0] == "apply_lod_decimation_plan"
    assert fb.calls[0][1] == {
        "query": "pine", "category": "tree", "max_objects": 50, "min_triangles_per_object": 30000,
        "create_proxy_lods": True, "replace_with_proxy": True, "disable_shadows": False,
        "mark_static": False, "lod0_screen_relative_height": 0.4, "lod1_screen_relative_height": 0.1,
    }


def test_apply_lod_decimation_plan_defaults(monkeypatch):
    fb = _FakeBridge()
    monkeypatch.setattr(ut, "_UNITY", fb)
    ut.unity_apply_lod_decimation_plan()
    assert fb.calls[0][1] == {
        "query": "", "category": "tree", "max_objects": 150, "min_triangles_per_object": 25000,
        "create_proxy_lods": True, "replace_with_proxy": False, "disable_shadows": True,
        "mark_static": True, "lod0_screen_relative_height": 0.38, "lod1_screen_relative_height": 0.08,
    }


def test_apply_lod_decimation_plan_no_bridge(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)
    assert ut.unity_apply_lod_decimation_plan()["ok"] is False


# --- registry: all 15 new tools are actually exposed to the LLM ------------

def test_all_wired_tools_registered():
    from unitytools.core.tool_registry import get_all_tools
    names = {t.name for t in get_all_tools()}
    expected = {
        "unity_apply_material_palette", "unity_diagnose_material_issues",
        "unity_repair_material_issues", "unity_repair_texture_import_settings",
        "unity_create_optimized_forest_scene", "unity_get_scene_catalog",
        "unity_find_scene_objects_semantic", "unity_delete_scene_objects_semantic",
        "unity_run_visual_qa", "unity_create_scene_snapshot",
        "unity_restore_scene_snapshot", "unity_profile_scene_performance",
        "unity_optimize_editor_performance", "unity_analyze_lod_decimation_candidates",
        "unity_apply_lod_decimation_plan",
    }
    assert expected.issubset(names)
