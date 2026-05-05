"""Tool argument alias normalization tests."""
from __future__ import annotations

from unitytools.core.config import Config
from unitytools.core.orchestrator import Orchestrator
from unitytools.core.tool_registry import get_tool
import unitytools.tools.scene_intelligence_tools  # noqa: F401 - registers tools


def run_test():
    orch = Orchestrator(Config.load())
    spec = get_tool("unity_apply_material_palette")
    assert spec is not None

    normalized = orch._normalize_tool_params(
        "unity_apply_material_palette",
        {"object": "trees", "color_palette": "forest", "max_results": 50},
        spec.fn,
    )
    assert normalized == {
        "query": "trees",
        "palette": "forest",
        "max": 50,
        "category": "tree",
    }

    normalized = orch._normalize_tool_params(
        "unity_apply_material_palette",
        {"target": "zemin", "colors": "ground", "count": 5},
        spec.fn,
    )
    assert normalized == {
        "query": "zemin",
        "palette": "ground",
        "max": 5,
        "category": "ground",
    }

    print("OK tool argument aliases")


if __name__ == "__main__":
    run_test()
