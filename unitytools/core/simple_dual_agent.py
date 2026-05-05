"""Simplified dual-agent: Route requests to appropriate model based on complexity.

Simple approach:
- Complex requests (planning, multi-step) -> Qwen 2.5:14b by default
- Simple requests (single tool call) -> Qwen 2.5:14b by default

No master-worker hierarchy, just smart routing.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Callable, Optional

from .config import Config
from .orchestrator import Orchestrator

logger = logging.getLogger(__name__)


# Keywords that indicate complex requests
COMPLEX_KEYWORDS = [
    "create.*forest",
    "build.*scene",
    "setup.*environment",
    "generate.*level",
    "design.*layout",
    "multiple.*objects",
    "\\d+.*objects",  # "20 trees", "5 cubes"
    "scatter",
    "distribute",
    "arrange",
    "organize",
]

# Keywords that indicate simple requests
SIMPLE_KEYWORDS = [
    "list",
    "show",
    "get",
    "find",
    "search",
    "what",
    "how many",
    "count",
]


class SimpleDualAgent:
    """Smart model router based on request complexity."""

    def __init__(
        self,
        config: Config,
        complex_model: str = "qwen2.5:14b-instruct",
        simple_model: str = "qwen2.5:14b-instruct",
    ) -> None:
        self.config = config
        self.complex_model = complex_model
        self.simple_model = simple_model

        # Create two orchestrators
        complex_config = self._clone_config(config, complex_model)
        self.complex_orch = Orchestrator(complex_config)

        simple_config = self._clone_config(config, simple_model)
        self.simple_orch = Orchestrator(simple_config)

        logger.info(
            "SimpleDualAgent: Complex=%s, Simple=%s",
            complex_model,
            simple_model,
        )

    def reset(self) -> None:
        """Reset both orchestrators."""
        self.complex_orch.reset()
        self.simple_orch.reset()

    def chat(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, Any], None]] = None,
        on_model_selected: Optional[Callable[[str], None]] = None,
        max_iterations: int = 10,
    ) -> Any:
        """Route request to appropriate model and execute.

        Args:
            user_message: User's request
            on_tool_call: Callback when tool is called
            on_tool_result: Callback when tool returns
            on_model_selected: Callback with selected model name
            max_iterations: Max tool-calling iterations

        Returns:
            OrchestratorResult
        """
        # Determine complexity
        is_complex = self._is_complex_request(user_message)
        selected_model = self.complex_model if is_complex else self.simple_model
        orch = self.complex_orch if is_complex else self.simple_orch

        logger.info(
            "Request routed to %s (complex=%s)",
            selected_model,
            is_complex,
        )

        if on_model_selected:
            on_model_selected(selected_model)

        # Execute with selected orchestrator
        return orch.chat(
            user_message,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
            max_iterations=max_iterations,
        )

    def _is_complex_request(self, message: str) -> bool:
        """Determine if request is complex based on keywords."""
        lower = message.lower()

        # Check for simple keywords first (higher priority)
        for pattern in SIMPLE_KEYWORDS:
            if re.search(pattern, lower):
                return False

        # Check for complex keywords
        for pattern in COMPLEX_KEYWORDS:
            if re.search(pattern, lower):
                return True

        # Default: if message is long, it's probably complex
        return len(message.split()) > 15

    @staticmethod
    def _clone_config(config: Config, model: str) -> Config:
        """Clone config with different model."""
        import copy
        new_config = copy.deepcopy(config)
        new_config.ollama_model = model
        return new_config
