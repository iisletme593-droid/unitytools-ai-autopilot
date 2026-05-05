"""Advanced context management for dual-agent.

Features:
- Scene state tracking
- Asset inventory
- Recent actions history
- Context summarization
- Relevance filtering
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SceneContext:
    """Current Unity scene state."""
    objects: list[dict[str, Any]] = field(default_factory=list)
    object_count: int = 0
    bounds: dict[str, float] = field(default_factory=dict)
    has_camera: bool = False
    has_light: bool = False
    last_updated: float = 0.0


@dataclass
class AssetContext:
    """Available assets in project."""
    trees: list[str] = field(default_factory=list)
    rocks: list[str] = field(default_factory=list)
    props: list[str] = field(default_factory=list)
    characters: list[str] = field(default_factory=list)
    total_assets: int = 0
    last_scanned: float = 0.0


@dataclass
class ActionHistory:
    """Recent actions taken."""
    actions: list[dict[str, Any]] = field(default_factory=list)
    max_size: int = 50
    
    def add(self, action: dict[str, Any]) -> None:
        self.actions.append(action)
        if len(self.actions) > self.max_size:
            self.actions.pop(0)
    
    def get_recent(self, count: int = 10) -> list[dict[str, Any]]:
        return self.actions[-count:]


class ContextManager:
    """Manages context for intelligent decision making."""
    
    def __init__(self):
        self.scene = SceneContext()
        self.assets = AssetContext()
        self.history = ActionHistory()
        
        logger.info("ContextManager initialized")
    
    def update_scene(self, objects: list[dict[str, Any]]) -> None:
        """Update scene context from Unity."""
        import time
        
        self.scene.objects = objects
        self.scene.object_count = len(objects)
        self.scene.last_updated = time.time()
        
        # Analyze scene
        self.scene.has_camera = any(
            obj.get("name", "").lower().startswith("camera") or
            "camera" in obj.get("components", [])
            for obj in objects
        )
        
        self.scene.has_light = any(
            "light" in obj.get("name", "").lower() or
            "light" in str(obj.get("components", [])).lower()
            for obj in objects
        )
        
        # Calculate bounds
        if objects:
            positions = [
                obj.get("position", {})
                for obj in objects
                if "position" in obj
            ]
            if positions:
                xs = [p.get("x", 0) for p in positions]
                ys = [p.get("y", 0) for p in positions]
                zs = [p.get("z", 0) for p in positions]
                
                self.scene.bounds = {
                    "min_x": min(xs),
                    "max_x": max(xs),
                    "min_y": min(ys),
                    "max_y": max(ys),
                    "min_z": min(zs),
                    "max_z": max(zs),
                }
        
        logger.debug(f"Scene updated: {self.scene.object_count} objects")
    
    def update_assets(self, asset_type: str, assets: list[str]) -> None:
        """Update asset inventory."""
        import time
        
        if asset_type == "trees":
            self.assets.trees = assets
        elif asset_type == "rocks":
            self.assets.rocks = assets
        elif asset_type == "props":
            self.assets.props = assets
        elif asset_type == "characters":
            self.assets.characters = assets
        
        self.assets.total_assets = (
            len(self.assets.trees) +
            len(self.assets.rocks) +
            len(self.assets.props) +
            len(self.assets.characters)
        )
        self.assets.last_scanned = time.time()
        
        logger.debug(f"Assets updated: {asset_type} = {len(assets)}")
    
    def record_action(self, action_type: str, details: dict[str, Any], success: bool) -> None:
        """Record an action in history."""
        import time
        
        self.history.add({
            "timestamp": time.time(),
            "type": action_type,
            "details": details,
            "success": success,
        })
    
    def get_context_summary(self) -> str:
        """Get human-readable context summary."""
        lines = []
        
        # Scene summary
        lines.append(f"Scene: {self.scene.object_count} objects")
        if self.scene.has_camera:
            lines.append("  - Has camera")
        if self.scene.has_light:
            lines.append("  - Has lighting")
        if self.scene.bounds:
            size_x = self.scene.bounds["max_x"] - self.scene.bounds["min_x"]
            size_z = self.scene.bounds["max_z"] - self.scene.bounds["min_z"]
            lines.append(f"  - Scene size: {size_x:.1f}x{size_z:.1f} units")
        
        # Assets summary
        if self.assets.total_assets > 0:
            lines.append(f"Assets: {self.assets.total_assets} total")
            if self.assets.trees:
                lines.append(f"  - {len(self.assets.trees)} tree types")
            if self.assets.rocks:
                lines.append(f"  - {len(self.assets.rocks)} rock types")
            if self.assets.props:
                lines.append(f"  - {len(self.assets.props)} prop types")
        
        # Recent actions
        recent = self.history.get_recent(5)
        if recent:
            lines.append(f"Recent actions: {len(recent)}")
            for action in recent[-3:]:
                action_type = action["type"]
                success = "✓" if action["success"] else "✗"
                lines.append(f"  {success} {action_type}")
        
        return "\n".join(lines)
    
    def get_context_for_planning(self) -> dict[str, Any]:
        """Get structured context for master agent planning."""
        return {
            "scene": {
                "object_count": self.scene.object_count,
                "has_camera": self.scene.has_camera,
                "has_light": self.scene.has_light,
                "bounds": self.scene.bounds,
                "is_empty": self.scene.object_count == 0,
            },
            "assets": {
                "trees_available": len(self.assets.trees),
                "rocks_available": len(self.assets.rocks),
                "props_available": len(self.assets.props),
                "characters_available": len(self.assets.characters),
                "tree_types": self.assets.trees[:5],  # Sample
                "rock_types": self.assets.rocks[:5],
            },
            "history": {
                "recent_actions": [
                    {
                        "type": a["type"],
                        "success": a["success"],
                    }
                    for a in self.history.get_recent(10)
                ],
                "recent_failures": [
                    a["type"]
                    for a in self.history.get_recent(20)
                    if not a["success"]
                ],
            },
        }
    
    def suggest_improvements(self) -> list[str]:
        """Suggest scene improvements based on context."""
        suggestions = []
        
        if not self.scene.has_camera:
            suggestions.append("Add a camera to view the scene")
        
        if not self.scene.has_light:
            suggestions.append("Add lighting for better visibility")
        
        if self.scene.object_count == 0:
            suggestions.append("Scene is empty - consider adding objects")
        
        if self.scene.object_count > 100:
            suggestions.append("Scene has many objects - consider optimization")
        
        # Check for failed actions
        recent_failures = [
            a for a in self.history.get_recent(10)
            if not a["success"]
        ]
        if len(recent_failures) > 3:
            suggestions.append("Multiple recent failures - review approach")
        
        return suggestions
    
    def find_clear_area(self, radius: float = 10.0) -> Optional[dict[str, float]]:
        """Find a clear area in the scene for placing objects."""
        if self.scene.object_count == 0:
            return {"x": 0, "y": 0, "z": 0}
        
        # Simple heuristic: find area with fewest objects
        # In real implementation, would use spatial partitioning
        
        if self.scene.bounds:
            # Try center of scene
            center_x = (self.scene.bounds["min_x"] + self.scene.bounds["max_x"]) / 2
            center_z = (self.scene.bounds["min_z"] + self.scene.bounds["max_z"]) / 2
            
            # Check if center is clear
            objects_near_center = sum(
                1 for obj in self.scene.objects
                if "position" in obj and
                abs(obj["position"].get("x", 0) - center_x) < radius and
                abs(obj["position"].get("z", 0) - center_z) < radius
            )
            
            if objects_near_center < 3:
                return {"x": center_x, "y": 0, "z": center_z}
            
            # Try offset from center
            return {
                "x": center_x + radius * 2,
                "y": 0,
                "z": center_z + radius * 2,
            }
        
        return {"x": 0, "y": 0, "z": 0}
    
    def estimate_density(self) -> str:
        """Estimate scene density."""
        if self.scene.object_count == 0:
            return "empty"
        
        if not self.scene.bounds:
            return "unknown"
        
        area = (
            (self.scene.bounds["max_x"] - self.scene.bounds["min_x"]) *
            (self.scene.bounds["max_z"] - self.scene.bounds["min_z"])
        )
        
        if area == 0:
            return "concentrated"
        
        density = self.scene.object_count / area
        
        if density < 0.1:
            return "sparse"
        elif density < 0.5:
            return "moderate"
        elif density < 1.0:
            return "dense"
        else:
            return "very_dense"
