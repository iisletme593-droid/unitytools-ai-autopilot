"""Advanced memory and learning system for dual-agent.

Features:
- Long-term memory (successful patterns)
- Short-term memory (current session)
- Learning from mistakes
- Pattern recognition
- Context retrieval
"""
from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


# --- recall similarity (pure, GPU-free) ------------------------------------
# Generic particles/articles (en+tr) plus the ultra-common scene verbs that
# carry no discriminative signal (every request is "create/yap X"), so recall
# matches on the SUBJECT (forest, tower, dungeon), not the boilerplate.
_STOPWORDS = frozenset({
    "the", "a", "an", "to", "of", "in", "on", "and", "or", "for", "with", "is",
    "are", "be", "it", "this", "that", "my", "me", "please", "i", "you",
    "bir", "ve", "ile", "icin", "bu", "su", "o", "da", "de", "den", "dan", "ki",
    "mi", "mu", "ne", "gibi", "cok", "ben", "bana", "lutfen", "sen",
    "create", "make", "build", "add", "generate", "yap", "kur", "ekle",
    "olustur", "uret",
})

_TR_FOLD = str.maketrans({
    "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _normalize_token_set(text: str) -> set[str]:
    norm = (text or "").translate(_TR_FOLD).lower()
    tokens = (t.strip(".,;:!?()[]{}\"'`-_/") for t in norm.split())
    return {t for t in tokens if t}


def _content_tokens(text: str) -> set[str]:
    """Normalized, stopword-filtered, length>=2, non-numeric tokens."""
    return {
        t for t in _normalize_token_set(text)
        if len(t) >= 2 and not t.isdigit() and t not in _STOPWORDS
    }


def _idf(token: str, df: dict[str, int], n: int) -> float:
    """Smoothed inverse document frequency: rarer tokens weigh more."""
    return math.log((n + 1) / (df.get(token, 0) + 1)) + 1.0


@dataclass
class MemoryEntry:
    """Single memory entry."""
    timestamp: float
    request: str
    plan: dict[str, Any]
    execution: dict[str, Any]
    success: bool
    duration: float
    tools_used: list[str]
    errors: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)


@dataclass
class Pattern:
    """Recognized pattern from past experiences."""
    pattern_type: str  # "request_type", "tool_sequence", "error_recovery"
    signature: str
    success_rate: float
    occurrences: int
    best_approach: dict[str, Any]
    common_pitfalls: list[str]


class MemorySystem:
    """Long-term and short-term memory for dual-agent."""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / ".unitytools" / "memory"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Short-term memory (current session)
        self.session_memories: list[MemoryEntry] = []

        # Long-term memory (persistent)
        self.long_term_file = self.storage_path / "long_term_memory.jsonl"
        # Long-term entries loaded from disk (prior sessions). Capped to the most
        # recent N because the file is append-only and can grow unbounded.
        self.long_term_memories: list[MemoryEntry] = []
        self.max_long_term_recall = 500

        # Patterns (learned from experience)
        self.patterns: dict[str, Pattern] = {}
        self.patterns_file = self.storage_path / "patterns.json"

        # Load existing data (patterns + prior-session memories -> cross-session recall)
        self._load_patterns()
        self._load_long_term()

        logger.info(f"MemorySystem initialized: {self.storage_path}")
    
    def remember(self, entry: MemoryEntry) -> None:
        """Store a memory entry."""
        # Add to session
        self.session_memories.append(entry)
        
        # Persist to long-term
        self._append_to_long_term(entry)
        
        # Learn from this experience
        self._learn_from_entry(entry)
        
        logger.debug(f"Remembered: {entry.request[:50]}... (success={entry.success})")
    
    def recall_similar(self, request: str, limit: int = 5) -> list[MemoryEntry]:
        """Recall similar past experiences from THIS session and PRIOR sessions.

        Searches both the in-process session memories (freshest) and the
        long-term memories loaded from disk at init, so learning persists across
        restarts. Entries present in both are de-duplicated by (timestamp, request).

        Similarity is an IDF-weighted Jaccard over Turkish-normalized, stopword-
        filtered tokens (not a raw overlap count): length-normalized, and rewards
        sharing distinctive subject words (e.g. "dungeon") over boilerplate. Pure
        Python — no neural embeddings (GPU-free).
        """
        # Build a de-duplicated pool with cached token sets.
        seen: set[tuple[float, str]] = set()
        pool: list[tuple[MemoryEntry, set[str]]] = []
        for entry in [*self.session_memories, *self.long_term_memories]:
            key = (entry.timestamp, entry.request)
            if key in seen:
                continue
            seen.add(key)
            pool.append((entry, _content_tokens(entry.request)))
        if not pool:
            return []

        # Document frequencies over the pool (for IDF weighting).
        df: dict[str, int] = {}
        for _entry, toks in pool:
            for t in toks:
                df[t] = df.get(t, 0) + 1
        n = len(pool)

        query = _content_tokens(request)
        if not query:  # query was all stopwords/numbers — fall back to raw tokens
            query = _normalize_token_set(request)
        if not query:
            return []

        scored: list[tuple[float, MemoryEntry]] = []
        for entry, toks in pool:
            shared = query & toks
            if not shared:
                continue
            union = query | toks
            num = sum(_idf(t, df, n) for t in shared)
            den = sum(_idf(t, df, n) for t in union)
            score = num / den if den else 0.0
            scored.append((score, entry))

        # Stable sort: session entries already precede long-term ones on ties.
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:limit]]
    
    def get_pattern(self, request: str) -> Optional[Pattern]:
        """Get the learned pattern for this request's class (if any).

        Unified with _classify_request so the recall taxonomy matches the learning
        taxonomy (they used to diverge) and so Turkish requests resolve too.
        """
        return self.patterns.get(self._classify_request(request))
    
    def get_lessons(self, request: str) -> list[str]:
        """Get lessons learned from similar past requests."""
        similar = self.recall_similar(request, limit=10)
        
        lessons = []
        for entry in similar:
            if not entry.success and entry.lessons:
                lessons.extend(entry.lessons)
        
        # Deduplicate
        return list(set(lessons))
    
    def get_success_rate(self, pattern_type: str) -> float:
        """Get success rate for a pattern type."""
        pattern = self.patterns.get(pattern_type)
        return pattern.success_rate if pattern else 0.5
    
    def _learn_from_entry(self, entry: MemoryEntry) -> None:
        """Learn patterns from this entry."""
        # Classify request type
        pattern_type = self._classify_request(entry.request)
        
        if pattern_type not in self.patterns:
            self.patterns[pattern_type] = Pattern(
                pattern_type=pattern_type,
                signature=self._extract_signature(entry.request),
                success_rate=1.0 if entry.success else 0.0,
                occurrences=1,
                best_approach=entry.plan if entry.success else {},
                common_pitfalls=entry.errors if not entry.success else [],
            )
        else:
            pattern = self.patterns[pattern_type]
            pattern.occurrences += 1
            
            # Update success rate (exponential moving average)
            alpha = 0.3
            pattern.success_rate = (
                alpha * (1.0 if entry.success else 0.0) +
                (1 - alpha) * pattern.success_rate
            )
            
            # Update best approach if this was better
            if entry.success and entry.duration < pattern.best_approach.get("duration", float('inf')):
                pattern.best_approach = {
                    "plan": entry.plan,
                    "duration": entry.duration,
                    "tools": entry.tools_used,
                }
            
            # Collect common pitfalls
            if not entry.success:
                pattern.common_pitfalls.extend(entry.errors)
                pattern.common_pitfalls = list(set(pattern.common_pitfalls))[:10]  # Keep top 10
        
        # Save patterns
        self._save_patterns()
    
    def _classify_request(self, request: str) -> str:
        """Classify request into a pattern type (English + Turkish keywords).

        Turkish matters because the autopilot is driven mostly in Turkish; without
        these terms learned patterns would almost never resolve for real usage.
        """
        r = request.lower()

        def has(*words: str) -> bool:
            return any(w in r for w in words)

        if has("create", "make", "build", "kur", "olustur", "oluştur", "yap", "ekle", "insa", "inşa"):
            if has("forest", "tree", "orman", "agac", "ağaç", "cam ", "çam"):
                return "create_forest"
            if has("rock", "boulder", "kaya", "tas", "taş", "stone"):
                return "create_rock_field"
            if has("cube", "sphere", "cylinder", "capsule", "kup", "küp", "kure", "küre", "silindir"):
                return "create_primitives"
            return "create_objects"
        if has("list", "show", "get", "listele", "goster", "göster", "bul", "katalog"):
            return "query_scene"
        if has("place", "scatter", "distribute", "yerlestir", "yerleştir", "dagit", "dağıt", "serp"):
            return "scatter_objects"
        if has("delete", "remove", "sil", "kaldir", "kaldır", "temizle"):
            return "delete_objects"
        if has("move", "position", "tasi", "taşı", "konumlandir", "konumlandır", "kaydir", "kaydır"):
            return "transform_objects"
        return "general"
    
    def _extract_signature(self, request: str) -> str:
        """Extract signature from request (for pattern matching)."""
        # Simple: just lowercase and remove numbers
        import re
        sig = request.lower()
        sig = re.sub(r'\d+', 'N', sig)  # Replace numbers with N
        return sig[:100]  # Limit length
    
    def _append_to_long_term(self, entry: MemoryEntry) -> None:
        """Append entry to long-term storage."""
        try:
            with open(self.long_term_file, 'a', encoding='utf-8') as f:
                data = {
                    "timestamp": entry.timestamp,
                    "request": entry.request,
                    "plan": entry.plan,
                    "execution": entry.execution,
                    "success": entry.success,
                    "duration": entry.duration,
                    "tools_used": entry.tools_used,
                    "errors": entry.errors,
                    "lessons": entry.lessons,
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to append to long-term memory: {e}")
    
    def _save_patterns(self) -> None:
        """Save patterns to disk."""
        try:
            data = {
                name: {
                    "pattern_type": p.pattern_type,
                    "signature": p.signature,
                    "success_rate": p.success_rate,
                    "occurrences": p.occurrences,
                    "best_approach": p.best_approach,
                    "common_pitfalls": p.common_pitfalls,
                }
                for name, p in self.patterns.items()
            }
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save patterns: {e}")
    
    def _load_patterns(self) -> None:
        """Load patterns from disk."""
        if not self.patterns_file.exists():
            return
        
        try:
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for name, p in data.items():
                self.patterns[name] = Pattern(
                    pattern_type=p["pattern_type"],
                    signature=p["signature"],
                    success_rate=p["success_rate"],
                    occurrences=p["occurrences"],
                    best_approach=p["best_approach"],
                    common_pitfalls=p["common_pitfalls"],
                )
            
            logger.info(f"Loaded {len(self.patterns)} patterns from disk")
        except Exception as e:
            logger.warning(f"Failed to load patterns: {e}")

    def _load_long_term(self) -> None:
        """Load persisted long-term memories so recall works ACROSS sessions.

        Reads the JSONL written by _append_to_long_term and keeps the most recent
        `max_long_term_recall` entries. Malformed lines are skipped. Without this,
        long_term_memory.jsonl was write-only and cross-session learning never
        actually recalled anything (the central 'learns across sessions' goal).
        """
        if not self.long_term_file.exists():
            return
        try:
            with open(self.long_term_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception as e:
            logger.warning(f"Failed to read long-term memory: {e}")
            return

        loaded: list[MemoryEntry] = []
        for line in lines[-self.max_long_term_recall:]:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                loaded.append(MemoryEntry(
                    timestamp=float(d.get("timestamp", 0.0)),
                    request=str(d.get("request", "")),
                    plan=d.get("plan") or {},
                    execution=d.get("execution") or {},
                    success=bool(d.get("success", False)),
                    duration=float(d.get("duration", 0.0)),
                    tools_used=list(d.get("tools_used") or []),
                    errors=list(d.get("errors") or []),
                    lessons=list(d.get("lessons") or []),
                ))
            except Exception:
                continue  # skip malformed lines, don't fail recall

        self.long_term_memories = loaded
        logger.info(f"Loaded {len(loaded)} long-term memories from disk (cross-session recall)")
    
    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "session_memories": len(self.session_memories),
            "patterns_learned": len(self.patterns),
            "total_occurrences": sum(p.occurrences for p in self.patterns.values()),
            "average_success_rate": (
                sum(p.success_rate for p in self.patterns.values()) / len(self.patterns)
                if self.patterns else 0.0
            ),
        }
