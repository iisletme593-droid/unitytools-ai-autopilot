"""Tool registry: @tool decoratorlu fonksiyonları Claude'un anlayacağı schema'ya çevirir.

Kullanım:

    @tool(description="Bir küp oluştur")
    def create_cube(name: str, size: float = 1.0) -> dict:
        ...

Decorator otomatik olarak Claude'a gönderilecek JSON schema'yı üretir.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable, get_type_hints


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]


_REGISTRY: dict[str, ToolSpec] = {}


def tool(description: str, name: str | None = None) -> Callable:
    """Fonksiyonu Claude'a expose edilecek tool olarak kaydet."""

    def decorator(fn: Callable) -> Callable:
        tool_name = name or fn.__name__
        spec = ToolSpec(
            name=tool_name,
            description=description,
            input_schema=_build_schema(fn),
            fn=fn,
        )
        _REGISTRY[tool_name] = spec
        return fn

    return decorator


def _build_schema(fn: Callable) -> dict[str, Any]:
    """Fonksiyonun signature'ından JSON schema üret."""
    sig = inspect.signature(fn)
    hints = get_type_hints(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        py_type = hints.get(param_name, str)
        properties[param_name] = _py_type_to_json_schema(py_type)

        # Default yoksa required say
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


def _py_type_to_json_schema(py_type: type) -> dict[str, Any]:
    mapping = {
        str: {"type": "string"},
        int: {"type": "integer"},
        float: {"type": "number"},
        bool: {"type": "boolean"},
        list: {"type": "array"},
        dict: {"type": "object"},
    }
    # Sadece basit tipleri destekliyoruz şimdilik
    return mapping.get(py_type, {"type": "string"})


def get_all_tools() -> list[ToolSpec]:
    return list(_REGISTRY.values())


def get_tool(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def to_anthropic_format() -> list[dict[str, Any]]:
    """Anthropic API'nin beklediği `tools` parametresi formatına çevir."""
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "input_schema": spec.input_schema,
        }
        for spec in _REGISTRY.values()
    ]

def to_openai_tool_format() -> list[dict[str, Any]]:
    """OpenAI/Ollama compatible function-tool schema."""
    return [
        {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.input_schema,
            },
        }
        for spec in _REGISTRY.values()
    ]
