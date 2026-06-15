"""P7 (cycle 32): living scenes — decorative behaviours as scene juice.

plan_ambient_decor places N props and cycles decorative behaviours
(bob/orbit/rotate/wander) over them. unity_animate_group wraps it with the same
execute=False(plan)/execute=True(build) contract as the games. Not a game — no
player or goal. Pure + deterministic; no recompile triggered here.
"""
import pytest

import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import plan_ambient_decor, DECOR_BEHAVIOURS, group_execution_plan
from unitytools.core.gameplay import generate_behaviour_script
from unitytools.core.game_studio_actions import plan_unity_fast_action


def test_decor_plan_structure():
    plan = plan_ambient_decor(count=8)
    assert plan["ok"] is True and plan["decor"] == "ambient"
    # one placement step then one behaviour per prop
    assert plan["steps"][0]["tool"] == "unity_place_primitives"
    assert plan["steps"][0]["kwargs"]["name_prefix"] == "Decor"
    behaviour_steps = [s for s in plan["steps"] if "script_behaviour" in s]
    assert len(behaviour_steps) == 8
    assert [s["script_behaviour"]["object"] for s in behaviour_steps] == [f"Decor_{i}" for i in range(8)]


def test_behaviours_are_cycled_across_props():
    plan = plan_ambient_decor(count=8)
    used = [s["script_behaviour"]["behaviour"] for s in plan["steps"] if "script_behaviour" in s]
    # cycles the default decor set: Decor_0->bob, _1->orbit, _2->rotate, _3->wander, _4->bob...
    assert used == [DECOR_BEHAVIOURS[i % len(DECOR_BEHAVIOURS)] for i in range(8)]
    # and there is NO player/goal/collectible — this is decor, not a game
    assert not ({"player", "goal", "collectible", "killzone"} & set(used))


def test_every_decor_behaviour_has_a_template():
    for b in DECOR_BEHAVIOURS:
        assert generate_behaviour_script(b)["ok"] is True


def test_custom_behaviours_validated_and_aliased():
    # 'don' is a Turkish alias of rotate; 'teleport' is unknown and must be dropped
    plan = plan_ambient_decor(count=4, behaviours=["don", "teleport", "bob"])
    assert plan["behaviours"] == ["rotate", "bob"]            # teleport dropped, don->rotate
    # nothing valid -> falls back to the default set, never empty
    fallback = plan_ambient_decor(count=4, behaviours=["teleport", "nonsense"])
    assert fallback["behaviours"] == list(DECOR_BEHAVIOURS)


def test_count_clamped():
    assert plan_ambient_decor(count=0)["count"] == 1
    assert plan_ambient_decor(count=999)["count"] == 200


def test_tool_dry_run_default_no_scene_changes(monkeypatch):
    monkeypatch.setattr(ut, "_UNITY", None)                   # dry-run must not need a bridge
    r = ut.unity_animate_group(count=6)
    assert r["ok"] is True and r["dry_run"] is True
    assert r["decor"] == "ambient" and r["count"] == 6


def test_tool_registered():
    import unitytools.tools  # noqa: F401
    from unitytools.core.tool_registry import get_tool
    assert get_tool("unity_animate_group") is not None


def test_intent_routes_to_animate_group():
    for prompt in ["sahneyi canlandir", "yasayan sahne kur", "animate the scene"]:
        step = plan_unity_fast_action(prompt)["steps"][0]
        assert step["tool"] == "unity_animate_group", prompt


def test_decor_groups_for_one_recompile():
    grouped = group_execution_plan(plan_ambient_decor(count=8)["steps"])
    # 4 unique decor scripts regardless of prop count -> one recompile
    assert set(grouped["script_behaviours"]) == set(DECOR_BEHAVIOURS)
    assert len(grouped["attachments"]) == 8
