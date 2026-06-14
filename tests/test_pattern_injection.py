"""P3 learning (cycle 2): learned patterns now reach the master planner prompt.

Before this, MemorySystem.get_pattern computed a Pattern (success rate, best-approach
tools, pitfalls) that dual_agent never injected into _build_master_prompt, so learning
had no effect on planning. format_pattern_section closes that gap.
"""
import time

from unitytools.core.dual_agent import format_pattern_section
from unitytools.core.memory_system import MemorySystem, MemoryEntry, Pattern


def test_none_pattern_renders_empty():
    assert format_pattern_section(None) == ""


def test_pattern_section_includes_rate_tools_and_pitfalls():
    p = Pattern(
        pattern_type="create_forest",
        signature="create a forest of N trees",
        success_rate=0.83,
        occurrences=6,
        best_approach={"tools": ["unity_create_optimized_forest_scene"], "duration": 2.1},
        common_pitfalls=["too many trees lag the editor on this machine"],
    )
    section = format_pattern_section(p)
    assert "LEARNED PATTERN" in section
    assert "create_forest" in section
    assert "83%" in section
    assert "6 run" in section
    assert "unity_create_optimized_forest_scene" in section
    assert "too many trees lag the editor on this machine" in section


def test_pattern_without_tools_still_renders_header():
    # First-occurrence patterns store best_approach as the raw plan (no 'tools' key).
    p = Pattern(
        pattern_type="scatter_objects",
        signature="scatter rocks",
        success_rate=1.0,
        occurrences=1,
        best_approach={"goal": "scatter rocks"},
        common_pitfalls=[],
    )
    section = format_pattern_section(p)
    assert "scatter_objects" in section
    assert "100%" in section
    # no crash, no tools line
    assert "best-approach tools" not in section


def test_learned_pattern_flows_from_memory_to_prompt_section(tmp_path):
    """End-to-end: learn a request -> get_pattern -> render a usable prompt section."""
    m = MemorySystem(storage_path=tmp_path)
    m.remember(MemoryEntry(
        timestamp=time.time(),
        request="create a forest of pine trees",
        plan={"goal": "forest"},
        execution={},
        success=True,
        duration=2.0,
        tools_used=["unity_create_optimized_forest_scene"],
    ))
    pattern = m.get_pattern("create a forest of pine trees")
    assert pattern is not None
    section = format_pattern_section(pattern)
    assert "create_forest" in section
    assert "100%" in section


def test_turkish_requests_classify_and_recall(tmp_path):
    """The autopilot is driven in Turkish; learned patterns must resolve for it."""
    m = MemorySystem(storage_path=tmp_path)
    assert m._classify_request("orman kur 40 cam agaci") == "create_forest"
    assert m._classify_request("sahnedeki kayalari sil") == "delete_objects"
    assert m._classify_request("kayalari yerlestir") == "scatter_objects"
    assert m._classify_request("sahneyi listele") == "query_scene"

    m.remember(MemoryEntry(
        timestamp=time.time(), request="orman kur 40 cam agaci", plan={"goal": "forest"},
        execution={}, success=True, duration=2.0, tools_used=["unity_create_optimized_forest_scene"],
    ))
    # A Turkish recall query now resolves the learned pattern.
    p = m.get_pattern("orman kur")
    assert p is not None and p.pattern_type == "create_forest"
    assert format_pattern_section(p) != ""
