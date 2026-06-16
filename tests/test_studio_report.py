"""P14 (cycle 72): the code-derived studio report -- the studio describing itself.

build_studio_report() produces a comprehensive markdown report computed entirely from
the live registries (BLUEPRINTS, the scripted-template + physics behaviour catalogs,
the tool registry), so it can never drift from what the studio can actually do. Exposed
as the `unity_studio_report` tool and the "studio raporu / capabilities" NL intent.
"""
import pytest

import unitytools.tools  # noqa: F401 - register all @tools so the report can count them
from unitytools.core.game_qa import build_studio_report, studio_health, _BEHAVIOUR_CATEGORIES
from unitytools.core.game_blueprint import BLUEPRINTS
from unitytools.core.gameplay import _SCRIPT_TEMPLATES, GAMEPLAY_BEHAVIOURS
from unitytools.core.game_studio_actions import plan_unity_fast_action
from unitytools.core.tool_registry import get_all_tools


REPORT = build_studio_report()


def test_report_lists_every_game_type():
    for gt in BLUEPRINTS:
        assert f"`{gt}`" in REPORT, f"report missing game type {gt}"
    # the heading count is code-derived from BLUEPRINTS
    assert f"## Game types ({len(BLUEPRINTS)})" in REPORT


def test_studio_health_audits_every_blueprint_clean():
    h = studio_health()
    assert h["game_count"] == len(BLUEPRINTS)
    assert h["all_valid"] and h["all_playable"] and h["all_coherent"]
    assert h["flagged"] == []                         # no game type has issues
    for g in h["games"]:
        assert g["valid"] and g["playable"] and g["coherent"]
        assert g["design_notes"] == []


def test_report_shows_an_ok_health_section():
    # the report surfaces the self-audit; with all games clean it reads OK N/N
    n = len(BLUEPRINTS)
    assert f"## Studio health: OK ({n}/{n})" in REPORT
    assert "passes the design critique" in REPORT


def test_report_counts_are_code_derived():
    unique_classes = {v[0] for v in _SCRIPT_TEMPLATES.values()}
    assert f"{len(unique_classes)} scripted MonoBehaviours" in REPORT
    assert f"{len(GAMEPLAY_BEHAVIOURS)} physics primitives" in REPORT
    assert f"{len(get_all_tools())} registered" in REPORT


def test_every_scripted_class_is_categorized_no_drift():
    # the drift guard: every unique MonoBehaviour class must be categorized exactly once,
    # so adding a new behaviour forces it into the report (the test fails until then)
    categorized_classes = set()
    for behs in _BEHAVIOUR_CATEGORIES.values():
        for b in behs:
            assert b in _SCRIPT_TEMPLATES, f"categorized behaviour {b!r} is not a real template"
            categorized_classes.add(_SCRIPT_TEMPLATES[b][0])
    all_classes = {v[0] for v in _SCRIPT_TEMPLATES.values()}
    assert categorized_classes == all_classes, f"uncategorized classes: {all_classes - categorized_classes}"


def test_report_surfaces_feel_loop_membership():
    # title/gameover/sound sections name the games that actually wire them in -- arena and
    # horde have all three, runner has title+sound (not gameover, it's endless)
    assert "## Game feel" in REPORT
    feel_section = REPORT.split("## Game feel")[1].split("## Persistence")[0]
    assert "arena" in feel_section and "horde" in feel_section and "runner" in feel_section


def test_report_mentions_persistence_and_determinism():
    assert "## Persistence" in REPORT and "unity_save_game" in REPORT
    assert "## Procedural & deterministic" in REPORT
    assert "no Math.random" in REPORT


def test_report_is_pure_ascii():
    assert all(ord(c) < 128 for c in REPORT)


def test_report_grows_when_a_game_type_is_added(monkeypatch):
    # drift proof: registering a fake blueprint makes the report list it automatically
    from unitytools.core import game_qa, game_blueprint
    fake = dict(game_blueprint.BLUEPRINTS)
    fake["zzztest"] = lambda count=5: game_blueprint.plan_collectathon_game(count)
    monkeypatch.setattr(game_blueprint, "BLUEPRINTS", fake)
    monkeypatch.setattr(game_qa, "BLUEPRINTS", fake)
    grown = build_studio_report()
    assert "`zzztest`" in grown
    assert f"## Game types ({len(fake)})" in grown


# --- tool + intent ---------------------------------------------------------

def test_tool_is_registered_and_pure():
    tool = {t.name: t for t in get_all_tools()}.get("unity_studio_report")
    assert tool is not None
    out = tool.fn()
    assert out["ok"] is True and "Game Studio Report" in out["report"]


@pytest.mark.parametrize("prompt", [
    "studio raporu ver",
    "studio report",
    "yeteneklerin neler",
    "what can you do",
    "capabilities",
])
def test_report_intent_routes(prompt):
    assert plan_unity_fast_action(prompt)["steps"][0]["tool"] == "unity_studio_report", prompt


def test_report_intent_does_not_steal_game_catalog():
    # "neler yapabilirsin / what games" still lists the games (the lighter catalog)
    assert plan_unity_fast_action("neler yapabilirsin")["steps"][0]["tool"] == "unity_game_catalog"
    assert plan_unity_fast_action("what games can you make")["steps"][0]["tool"] == "unity_game_catalog"
