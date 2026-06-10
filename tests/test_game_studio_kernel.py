"""Self-evolving GameStudio kernel tests."""
from __future__ import annotations

from unitytools.core.game_studio_kernel import GameStudioKernel
from unitytools.core.tool_registry import get_tool
import unitytools.tools.game_studio_tools  # noqa: F401 - registers tools


def test_game_studio_kernel_initializes_and_plans(tmp_path):
    kernel = GameStudioKernel(root=tmp_path, workspace="GameStudioData")

    arch = kernel.architecture()
    assert arch["ok"] is True
    assert len(arch["levels"]) == 6
    assert arch["levels"][-1]["name"] == "Self-Evolving Game Studio"

    initialized = kernel.initialize(seed_games=["arena_survivor"])
    assert initialized["ok"] is True
    assert (tmp_path / "GameStudioData" / "studio_manifest.json").exists()
    assert (tmp_path / "GameStudioData" / "experiments.jsonl").exists()
    assert (tmp_path / "GameStudioData" / "SELF_EVOLUTION_ROADMAP.md").exists()

    recorded = kernel.record_experiment(
        game_title="arena_survivor",
        prototype_type="combat_loop",
        hypothesis="Shorter enemy waves improve clarity.",
        changes=["Reduced wave length", "Added clearer HUD prompt"],
        metrics={"fun_score": 7, "clarity_score": 5, "fps_average": 90},
        outcome="promising",
    )
    assert recorded["ok"] is True

    plan = kernel.create_iteration_plan(game_title="arena_survivor", focus="clarity")
    assert plan["ok"] is True
    assert plan["recommended_next_agent"] in {
        "Global Director AI",
        "Game Design AI",
        "Level AI",
        "Art AI",
        "QA AI",
    }
    assert plan["iteration_plan"]


def test_game_studio_tools_are_registered():
    assert get_tool("gamestudio_get_evolution_architecture") is not None
    assert get_tool("gamestudio_initialize_self_evolving_studio") is not None
    assert get_tool("gamestudio_record_game_experiment") is not None
    assert get_tool("gamestudio_create_iteration_plan") is not None
