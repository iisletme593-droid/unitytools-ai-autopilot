"""Self-evolving GameStudio kernel.

This module is deliberately deterministic. The AI may propose and execute
experiments, but the project keeps an auditable memory of what was changed,
what was measured, and what should be tried next.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .game_studio_actions import list_templates


STUDIO_LEVELS: list[dict[str, Any]] = [
    {
        "level": 1,
        "name": "Basic Assistant",
        "scope": ["chat", "code_suggestion"],
        "gate": "Can explain and suggest, but does not own files.",
    },
    {
        "level": 2,
        "name": "Coding Agent",
        "scope": ["edit_files", "run_tests", "fix_simple_bugs"],
        "gate": "Can modify code and verify small changes.",
    },
    {
        "level": 3,
        "name": "Autonomous Engineering Agent",
        "scope": ["plan", "scan_repo", "implement", "debug", "self_correct"],
        "gate": "Can complete repo tasks end-to-end with tests.",
    },
    {
        "level": 4,
        "name": "Unreal Development Agent",
        "scope": ["cpp", "blueprint", "assets", "levels", "animation", "niagara", "build_packaging"],
        "gate": "Can operate inside Unreal Editor through tools.",
    },
    {
        "level": 5,
        "name": "Autonomous Game Director AI",
        "scope": ["creative_direction", "combat_redesign", "camera_vfx_audio", "level_pacing", "qa_iteration"],
        "gate": "Can make design decisions and implement a playable improvement loop.",
    },
    {
        "level": 6,
        "name": "Self-Evolving Game Studio",
        "scope": ["player_data", "fun_analysis", "procedural_iteration", "balance", "liveops", "new_game_generation"],
        "gate": "Can run measured experiments and evolve prototypes safely over time.",
    },
]


AGENT_ROLES: list[dict[str, Any]] = [
    {
        "name": "Global Director AI",
        "mission": "Owns product intent, scope, fun target, and milestone order.",
        "writes": ["studio brief", "milestone plan", "go/no-go decisions"],
    },
    {
        "name": "Game Design AI",
        "mission": "Designs core loop, mechanics, progression, economy, quests, and player fantasy.",
        "writes": ["game design docs", "balance tables", "quest/event specs"],
    },
    {
        "name": "Engineering AI",
        "mission": "Implements Unreal C++, Blueprint, Python editor automation, build, and test glue.",
        "writes": ["source code", "blueprint scaffolds", "automation scripts"],
    },
    {
        "name": "Art AI",
        "mission": "Chooses assets, art direction, palettes, materials, composition, and LOD budgets.",
        "writes": ["asset plans", "material palettes", "LOD/decimation plans"],
    },
    {
        "name": "Audio AI",
        "mission": "Plans music, ambience, SFX, feedback timing, and mix priorities.",
        "writes": ["audio cue lists", "mix notes", "implementation tasks"],
    },
    {
        "name": "Level AI",
        "mission": "Builds maps, pacing, landmarks, encounters, navigation, fog, lighting, and cameras.",
        "writes": ["level briefs", "blockout plans", "map iteration notes"],
    },
    {
        "name": "Balance AI",
        "mission": "Reads metrics and tunes difficulty, economy, cooldowns, enemy density, and reward curves.",
        "writes": ["balance patches", "metric reports", "tuning hypotheses"],
    },
    {
        "name": "LiveOps AI",
        "mission": "Plans events, retention loops, experiments, patch notes, and player-segment changes.",
        "writes": ["event plans", "release notes", "A/B experiment briefs"],
    },
    {
        "name": "QA AI",
        "mission": "Runs smoke tests, visual QA, performance budgets, regression notes, and rollback checks.",
        "writes": ["QA reports", "risk logs", "acceptance checklists"],
    },
]


EVOLUTION_LOOP: list[str] = [
    "Brief: define one playable hypothesis.",
    "Generate: create or update a small prototype slice.",
    "Instrument: define measurable fun, clarity, performance, and retention signals.",
    "Playtest: collect human notes or automated proxy metrics.",
    "Analyze: compare result against the hypothesis.",
    "Mutate: choose one improvement, one cut, and one risk reduction.",
    "Verify: run build/QA/performance checks.",
    "Remember: store the lesson so the next prototype starts smarter.",
]


DEFAULT_METRICS: dict[str, Any] = {
    "fun_score": None,
    "clarity_score": None,
    "difficulty_score": None,
    "session_minutes": None,
    "fps_average": None,
    "crash_count": 0,
    "notes": [],
}


@dataclass
class GameStudioKernel:
    """Small local kernel for auditable studio evolution."""

    root: Path = Path.cwd()
    workspace: str = "GameStudioData"

    @property
    def workspace_path(self) -> Path:
        return (self.root / self.workspace).resolve()

    @property
    def manifest_path(self) -> Path:
        return self.workspace_path / "studio_manifest.json"

    @property
    def experiments_path(self) -> Path:
        return self.workspace_path / "experiments.jsonl"

    @property
    def roadmap_path(self) -> Path:
        return self.workspace_path / "SELF_EVOLUTION_ROADMAP.md"

    def architecture(self) -> dict[str, Any]:
        return {
            "ok": True,
            "levels": STUDIO_LEVELS,
            "agent_roles": AGENT_ROLES,
            "evolution_loop": EVOLUTION_LOOP,
            "default_metrics": DEFAULT_METRICS,
            "templates": list_templates(),
            "workspace": str(self.workspace_path),
        }

    def initialize(self, seed_games: list[str] | None = None) -> dict[str, Any]:
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        seed_games = seed_games or ["arena_survivor", "small_rpg_village", "forest_extraction", "puzzle_dungeon"]
        manifest = {
            "ok": True,
            "created_at": _now(),
            "name": "Private Self-Evolving GameStudio",
            "current_level": 4,
            "target_level": 6,
            "safety_mode": "human_approved_mutation",
            "seed_games": seed_games,
            "levels": STUDIO_LEVELS,
            "agent_roles": AGENT_ROLES,
            "evolution_loop": EVOLUTION_LOOP,
            "rules": [
                "Never run destructive project-wide edits without an explicit snapshot or human approval.",
                "Every prototype must have a hypothesis and measurable acceptance criteria.",
                "Prefer small playable slices over huge unfinished systems.",
                "Record each experiment before using it as memory.",
                "Use Unreal tools for Unreal projects and Unity tools for Unity projects.",
            ],
        }
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if not self.experiments_path.exists():
            self.experiments_path.write_text("", encoding="utf-8")
        self.roadmap_path.write_text(_roadmap_markdown(seed_games), encoding="utf-8")
        return {
            "ok": True,
            "workspace": str(self.workspace_path),
            "manifest": str(self.manifest_path),
            "experiments": str(self.experiments_path),
            "roadmap": str(self.roadmap_path),
            "seed_games": seed_games,
        }

    def record_experiment(
        self,
        game_title: str,
        prototype_type: str = "unknown",
        hypothesis: str = "",
        changes: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        outcome: str = "unknown",
        notes: str = "",
    ) -> dict[str, Any]:
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": _now(),
            "game_title": game_title,
            "prototype_type": prototype_type,
            "hypothesis": hypothesis,
            "changes": changes or [],
            "metrics": {**DEFAULT_METRICS, **(metrics or {})},
            "outcome": outcome,
            "notes": notes,
        }
        with self.experiments_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        return {"ok": True, "experiment": payload, "path": str(self.experiments_path)}

    def create_iteration_plan(self, game_title: str = "", focus: str = "fun", last_n: int = 5) -> dict[str, Any]:
        experiments = self._read_experiments()
        if game_title:
            experiments = [row for row in experiments if row.get("game_title", "").lower() == game_title.lower()]
        recent = experiments[-max(1, last_n):]
        weak_points = _infer_weak_points(recent, focus)
        plan = {
            "ok": True,
            "game_title": game_title or "next prototype",
            "focus": focus,
            "recent_experiments": recent,
            "iteration_plan": [
                {
                    "phase": "read",
                    "tasks": [
                        "Scan current Unreal project and active level.",
                        "Read asset catalog, gameplay tags, maps, UI assets, and existing prototype notes.",
                    ],
                },
                {
                    "phase": "mutate",
                    "tasks": [
                        f"Improve the weakest signal first: {weak_points[0]}.",
                        "Make one small playable change, not ten unfinished systems.",
                        "Add names/tags so future agents can find every new actor and asset.",
                    ],
                },
                {
                    "phase": "verify",
                    "tasks": [
                        "Run editor ping/smoke checks.",
                        "Capture performance and visual QA notes.",
                        "Record experiment result into GameStudio memory.",
                    ],
                },
            ],
            "recommended_next_agent": _recommended_agent(focus, weak_points),
            "weak_points": weak_points,
        }
        return plan

    def _read_experiments(self) -> list[dict[str, Any]]:
        if not self.experiments_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.experiments_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _infer_weak_points(experiments: list[dict[str, Any]], focus: str) -> list[str]:
    if not experiments:
        return [focus, "prototype clarity", "basic smoke test"]
    scores: dict[str, float] = {}
    for row in experiments:
        metrics = row.get("metrics") or {}
        for key in ("fun_score", "clarity_score", "difficulty_score", "fps_average"):
            value = metrics.get(key)
            if isinstance(value, (int, float)):
                scores.setdefault(key, 0.0)
                scores[key] += float(value)
    if not scores:
        return [focus, "missing metrics", "playtest notes"]
    averaged = {key: value / max(1, len(experiments)) for key, value in scores.items()}
    ordered = sorted(averaged.items(), key=lambda item: item[1])
    weak = [key.replace("_score", "").replace("_", " ") for key, _ in ordered[:3]]
    if focus not in " ".join(weak):
        weak.insert(0, focus)
    return weak[:3]


def _recommended_agent(focus: str, weak_points: list[str]) -> str:
    text = " ".join([focus] + weak_points).lower()
    focus_text = (focus or "").lower()
    if any(w in focus_text for w in ("fun", "combat", "loop", "difficulty", "clarity")):
        return "Game Design AI"
    if any(w in focus_text for w in ("fps", "performance", "crash", "smoke", "qa")):
        return "QA AI"
    if any(w in focus_text for w in ("level", "map", "pacing", "navigation")):
        return "Level AI"
    if any(w in focus_text for w in ("art", "asset", "material", "palette")):
        return "Art AI"
    if any(w in text for w in ("fps", "performance", "crash", "smoke")):
        return "QA AI"
    if any(w in text for w in ("fun", "combat", "loop", "difficulty")):
        return "Game Design AI"
    if any(w in text for w in ("level", "map", "pacing", "navigation")):
        return "Level AI"
    if any(w in text for w in ("art", "asset", "material", "palette")):
        return "Art AI"
    return "Global Director AI"


def _roadmap_markdown(seed_games: list[str]) -> str:
    seed_list = "\n".join(f"- {name}" for name in seed_games)
    roles = "\n".join(f"- {role['name']}: {role['mission']}" for role in AGENT_ROLES)
    loop = "\n".join(f"{idx}. {step}" for idx, step in enumerate(EVOLUTION_LOOP, 1))
    return f"""# Self-Evolving GameStudio Roadmap

This workspace is the local memory for a private Unreal/Unity GameStudio.

## Seed Games
{seed_list}

## Agent Roles
{roles}

## Evolution Loop
{loop}

## First Year Target
- Month 1-2: reliable Level 4 Unreal Development Agent.
- Month 3-5: Level 5 Game Director with playable prototype iteration.
- Month 6-12: controlled Level 6 loop: player data -> analysis -> safe mutation -> QA -> memory.

## Safety Contract
- No uncontrolled self-modification.
- No destructive edits without snapshot or explicit approval.
- Every mutation must be measurable.
- Keep experiments small, playable, and reversible.
"""
