"""P7 (cycle 38): inject game capabilities into the master planner prompt.

build_game_capabilities_summary() renders a compact, CODE-DERIVED block (from
summarize_catalog) listing the game types and the tools each request routes to,
so the master planner knows the studio can make games. It must stay in sync with
BLUEPRINTS (not hardcoded). The block is injected into _build_master_prompt.
"""
from unitytools.core.game_qa import build_game_capabilities_summary
from unitytools.core.game_blueprint import BLUEPRINTS


def test_summary_lists_every_game_type():
    text = build_game_capabilities_summary()
    for gt in BLUEPRINTS:
        assert gt in text, f"capability summary missing game type {gt}"


def test_summary_names_the_routing_tools():
    text = build_game_capabilities_summary()
    for tool in ("unity_build_simple_game", "unity_assess_game",
                 "unity_game_variations", "unity_game_catalog"):
        assert tool in text, f"capability summary missing tool {tool}"


def test_summary_is_code_derived_not_hardcoded():
    # the game count in the text must equal the live blueprint count
    text = build_game_capabilities_summary()
    assert str(len(BLUEPRINTS)) in text
    # mentions behaviours and the execute/recompile safety note
    assert "behaviours" in text.lower()
    assert "execute=False" in text


def test_summary_is_injected_into_master_prompt(monkeypatch):
    # build the master prompt and confirm the capabilities block is present
    import unitytools.core.dual_agent as da

    class _Stub:
        # only the methods _build_master_prompt touches
        def _engine_hint(self):
            return "ENGINE: unity"

    # call the real method against a stub so we don't need a full orchestrator
    prompt = da.DualAgentOrchestrator._build_master_prompt(
        _Stub(),
        user_message="bana bir oyun yap",
        context_info="",
        similar_experiences=[],
        learned_lessons=[],
    )
    assert "GAME STUDIO CAPABILITIES" in prompt
    assert "unity_build_simple_game" in prompt
    # every game type made it into the assembled prompt
    for gt in BLUEPRINTS:
        assert gt in prompt
