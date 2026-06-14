"""P6 (cycle 6): deterministic Unity fast-action planner (the primary engine).

plan_unity_fast_action mirrors the Unreal planner, mapping Turkish/English intents
to the existing unity_* tools so the studio loop runs on Unity without an LLM
round-trip. Steps carry write flags; preflight routes accordingly.
"""
from unitytools.core.game_studio_actions import plan_unity_fast_action, preflight_prompt


def _tools(plan):
    return [s["tool"] for s in plan["steps"]]


def test_forest_with_count():
    plan = plan_unity_fast_action("orman kur 40 cam agaci")
    assert plan["steps"][0]["tool"] == "unity_create_optimized_forest_scene"
    assert plan["steps"][0]["kwargs"]["tree_count"] == 40
    assert plan["steps"][0]["write"] is True
    assert plan["safety_notes"]  # clearing the scene is flagged


def test_place_primitives_circle():
    plan = plan_unity_fast_action("20 kupu cember duzeninde yerlestir")
    step = plan["steps"][0]
    assert step["tool"] == "unity_place_primitives"
    assert step["kwargs"]["count"] == 20
    assert step["kwargs"]["pattern"] == "circle"
    assert step["kwargs"]["type"] == "Cube"


def test_quality_check_is_read_only_but_fix_is_write():
    assert _tools(plan_unity_fast_action("sahnenin kalitesini kontrol et")) == ["unity_run_visual_qa"]
    assert plan_unity_fast_action("sahnenin kalitesini kontrol et")["steps"][0]["write"] is False
    fix = plan_unity_fast_action("sahne kalitesini duzelt")["steps"][0]
    assert fix["tool"] == "unity_quality_pass"
    assert fix["write"] is True


def test_delete_is_destructive():
    plan = plan_unity_fast_action("sahnedeki kayalari sil")
    step = plan["steps"][0]
    assert step["tool"] == "unity_delete_scene_objects_semantic"
    assert step["write"] is True
    assert step["kwargs"]["query"] == "rock"
    assert plan["safety_notes"]


def test_compound_prompt_multiple_steps():
    plan = plan_unity_fast_action("once snapshot al sonra orman kur")
    tools = _tools(plan)
    assert tools[0] == "unity_create_scene_snapshot"
    assert "unity_create_optimized_forest_scene" in tools


def test_catalog_and_record_experiment():
    assert _tools(plan_unity_fast_action("sahneyi listele")) == ["unity_get_scene_catalog"]
    assert _tools(plan_unity_fast_action("deney kaydet ve ogren")) == ["gamestudio_record_scene_experiment"]


def test_empty_and_no_action():
    assert plan_unity_fast_action("")["reason"] == "empty"
    assert plan_unity_fast_action("merhaba nasilsin")["reason"] == "no action verb"


def test_planner_only_emits_real_tools():
    from unitytools.core.tool_registry import get_all_tools
    import unitytools.tools  # noqa: F401 - register
    registered = {t.name for t in get_all_tools()}
    prompts = ["orman kur 30 agac", "10 kup yerlestir", "kaliteyi duzelt", "kayalari sil",
               "isik kur", "fantasy renklendir", "agaclari bul", "performansi olc",
               "sahneyi listele", "snapshot al", "deney kaydet"]
    for p in prompts:
        for step in plan_unity_fast_action(p)["steps"]:
            assert step["tool"] in registered, f"{p} -> phantom tool {step['tool']}"


# --- preflight routing -----------------------------------------------------

def test_preflight_unity_write_route():
    pf = preflight_prompt("orman kur", engine="unity")
    assert pf["engine"] == "unity"
    assert pf["route"] == "fast_action"
    assert pf["risk"] == "write"
    assert "unity_create_optimized_forest_scene" in pf["recommended_tools"]


def test_preflight_unity_read_only_fallback():
    pf = preflight_prompt("sahnede ne var goster", engine="unity")
    assert pf["engine"] == "unity"
    # either a read-only fast_action step or the read-only fallback, never a write
    assert pf["risk"] in ("read_only",)
    assert all(t.startswith("unity_") for t in pf["recommended_tools"])
