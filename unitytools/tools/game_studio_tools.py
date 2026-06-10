"""Local GameStudio evolution tools."""
from __future__ import annotations

from typing import Any

from ..core.game_studio_actions import list_templates, plan_unreal_fast_action, preflight_prompt
from ..core.game_studio_kernel import GameStudioKernel
from ..core.tool_registry import tool


@tool(description="Return the Level 1-6 Self-Evolving GameStudio architecture, agent roles, and evolution loop.")
def gamestudio_get_evolution_architecture(workspace: str = "GameStudioData") -> dict:
    return GameStudioKernel(workspace=workspace).architecture()


@tool(description="List available GameStudio prototype templates and their safe trigger rules.")
def gamestudio_list_templates() -> dict:
    return {"ok": True, "templates": list_templates()}


@tool(description="Plan a deterministic safe Unreal fast-action from a user prompt without executing it.")
def gamestudio_plan_unreal_fast_action(text: str) -> dict:
    return plan_unreal_fast_action(text)


@tool(description="Classify a prompt before tool execution: route, risk level, template match, and recommended tools.")
def gamestudio_preflight_prompt(text: str, engine: str = "unreal") -> dict:
    return preflight_prompt(text, engine=engine)


@tool(description="Initialize local Self-Evolving GameStudio memory: manifest, roadmap, and experiment log under GameStudioData.")
def gamestudio_initialize_self_evolving_studio(
    workspace: str = "GameStudioData",
    seed_games: list[str] | None = None,
) -> dict:
    return GameStudioKernel(workspace=workspace).initialize(seed_games=seed_games)


@tool(description="Record one prototype/playtest/evolution experiment into local GameStudio memory.")
def gamestudio_record_game_experiment(
    game_title: str,
    prototype_type: str = "unknown",
    hypothesis: str = "",
    changes: list[str] | None = None,
    metrics: dict[str, Any] | None = None,
    outcome: str = "unknown",
    notes: str = "",
    workspace: str = "GameStudioData",
) -> dict:
    return GameStudioKernel(workspace=workspace).record_experiment(
        game_title=game_title,
        prototype_type=prototype_type,
        hypothesis=hypothesis,
        changes=changes,
        metrics=metrics,
        outcome=outcome,
        notes=notes,
    )


@tool(description="Create the next safe iteration plan from local GameStudio experiment memory.")
def gamestudio_create_iteration_plan(
    game_title: str = "",
    focus: str = "fun",
    last_n: int = 5,
    workspace: str = "GameStudioData",
) -> dict:
    return GameStudioKernel(workspace=workspace).create_iteration_plan(
        game_title=game_title,
        focus=focus,
        last_n=last_n,
    )
