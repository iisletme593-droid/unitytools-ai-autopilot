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
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
        """
        keywords = set(request.lower().split())

        seen: set[tuple[float, str]] = set()
        similar: list[tuple[int, MemoryEntry]] = []
        for entry in [*self.session_memories, *self.long_term_memories]:
            key = (entry.timestamp, entry.request)
            if key in seen:
                continue
            seen.add(key)
            entry_keywords = set(entry.request.lower().split())
            overlap = len(keywords & entry_keywords)
            if overlap > 0:
                similar.append((overlap, entry))

        # Sort by similarity (stable: session entries already come first on ties)
        similar.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in similar[:limit]]
    
    def get_pattern(self, request: str) -> Optional[Pattern]:
        """Get learned pattern for this type of request."""
        # Classify request type
        request_lower = request.lower()
        
        if "create" in request_lower and "forest" in request_lower:
            return self.patterns.get("create_forest")
        elif "create" in request_lower and ("cube" in request_lower or "sphere" in request_lower):
            return self.patterns.get("create_primitives")
        elif "list" in request_lower or "show" in request_lower:
            return self.patterns.get("query_scene")
        elif "place" in request_lower or "scatter" in request_lower:
            return self.patterns.get("scatter_objects")
        
        return None
    
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
        """Classify request into pattern type."""
        request_lower = request.lower()
        
        if "create" in request_lower:
            if "forest" in request_lower or "tree" in request_lower:
                return "create_forest"
            elif "rock" in request_lower or "boulder" in request_lower:
                return "create_rock_field"
            elif any(prim in request_lower for prim in ["cube", "sphere", "cylinder", "capsule"]):
                return "create_primitives"
            else:
                return "create_objects"
        elif "list" in request_lower or "show" in request_lower or "get" in request_lower:
            return "query_scene"
        elif "place" in request_lower or "scatter" in request_lower or "distribute" in request_lower:
            return "scatter_objects"
        elif "delete" in request_lower or "remove" in request_lower:
            return "delete_objects"
        elif "move" in request_lower or "position" in request_lower:
            return "transform_objects"
        else:
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
