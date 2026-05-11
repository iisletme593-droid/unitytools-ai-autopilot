"""Canonical filesystem layout for a studio project."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StudioPaths:
    """All paths under <project_root>/studio/.

    Single source of truth — code that reads or writes studio files goes
    through here so the layout can evolve in one place.
    """

    project_root: Path

    @property
    def root(self) -> Path:
        return self.project_root / "studio"

    @property
    def gdd(self) -> Path:
        return self.root / "gdd.md"

    @property
    def art_bible(self) -> Path:
        return self.root / "art_bible.md"

    @property
    def audio_brief(self) -> Path:
        return self.root / "audio_brief.md"

    @property
    def press_kit(self) -> Path:
        return self.root / "press_kit.md"

    @property
    def tutorial(self) -> Path:
        return self.root / "tutorial.md"

    @property
    def scene_catalog(self) -> Path:
        return self.root / "scene_catalog.md"

    @property
    def strings(self) -> Path:
        """Directory holding per-locale string tables (<code>.json)."""
        return self.root / "strings"

    @property
    def sprint_current(self) -> Path:
        return self.root / "sprint_current.md"

    @property
    def backlog(self) -> Path:
        return self.root / "backlog.json"

    @property
    def decisions(self) -> Path:
        return self.root / "decisions.jsonl"

    @property
    def milestones(self) -> Path:
        return self.root / "milestones.json"

    @property
    def refs(self) -> Path:
        return self.root / "refs"

    @property
    def reviews(self) -> Path:
        return self.root / "reviews"

    @property
    def qa(self) -> Path:
        return self.root / "qa"

    @property
    def qa_screenshots(self) -> Path:
        return self.qa / "screenshots"

    @property
    def qa_diffs(self) -> Path:
        return self.qa / "diffs"

    @property
    def qa_regression(self) -> Path:
        return self.qa / "regression.jsonl"

    @property
    def memory(self) -> Path:
        return self.root / "memory"

    @property
    def archive_root(self) -> Path:
        return self.root / "archive"

    def archive(self, year: int) -> Path:
        return self.archive_root / f"{year}.json"

    @property
    def gitignore(self) -> Path:
        return self.root / ".gitignore"

    def daily_review(self, date_iso: str) -> Path:
        return self.reviews / f"{date_iso}.md"

    def all_dirs(self) -> list[Path]:
        return [self.root, self.refs, self.reviews, self.qa, self.qa_screenshots, self.qa_diffs, self.memory, self.archive_root, self.strings]

    def exists(self) -> bool:
        return self.root.is_dir()
