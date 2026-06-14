"""Tool registry: @tool decoratorlu fonksiyonları LLM provider'larının
anlayacağı JSON schema'ya çevirir.

Kullanım:

    @tool(description="Bir küp oluştur")
    def create_cube(name: str, size: float = 1.0) -> dict:
        ...

Decorator otomatik olarak Claude/Ollama'ya gönderilecek JSON schema'yı üretir.

Type ipuçları:
  * Optional[X]            -> {"type": X-json}                      (required değil)
  * Union[X, None]         -> aynı şey
  * list[X] / List[X]      -> {"type": "array", "items": {...X...}}
  * dict / dict[str, Any]  -> {"type": "object"}
  * Literal["a","b"]       -> {"type": "string", "enum": ["a","b"]}
  * Path / pathlib.Path    -> {"type": "string"}
"""
from __future__ import annotations

import inspect
import logging
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, get_type_hints

logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]


_REGISTRY: dict[str, ToolSpec] = {}

# Tracks duplicate tool-name registrations (last-import-wins silently shadows the
# earlier one). Populated at import time; surfaced via get_collisions() so a test
# can fail if two modules register the same @tool name.
_COLLISIONS: dict[str, list[str]] = {}


def tool(description: str, name: str | None = None) -> Callable:
    """Fonksiyonu LLM'e expose edilecek tool olarak kaydet."""

    def decorator(fn: Callable) -> Callable:
        tool_name = name or fn.__name__
        if tool_name in _REGISTRY:
            prev_mod = getattr(_REGISTRY[tool_name].fn, "__module__", "?")
            new_mod = getattr(fn, "__module__", "?")
            logger.warning(
                "Tool '%s' yeniden tanımlandı: %s onceki %s'i golgeliyor (sonuncu kazanir).",
                tool_name, new_mod, prev_mod,
            )
            _COLLISIONS.setdefault(tool_name, [prev_mod]).append(new_mod)
        spec = ToolSpec(
            name=tool_name,
            description=description,
            input_schema=_build_schema(fn),
            fn=fn,
        )
        _REGISTRY[tool_name] = spec
        return fn

    return decorator


# --------------------------------------------------------------- schema build

_PRIMITIVE_MAP: dict[type, dict[str, Any]] = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
    dict: {"type": "object"},
    type(None): {"type": "null"},
    Path: {"type": "string"},
}


def _build_schema(fn: Callable) -> dict[str, Any]:
    """Fonksiyonun signature'ından JSON schema üret."""
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn)
    except Exception:
        # PEP 604 unions vs. ile sorun olursa raw annotation'ları kullan
        hints = {p: (param.annotation if param.annotation is not inspect.Parameter.empty else str)
                 for p, param in sig.parameters.items()}

    properties: dict[str, Any] = {}
    required: list[str] = []
    extra_descriptions: dict[str, str] = {}

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        py_type = hints.get(param_name, str)
        prop_schema = _py_type_to_json_schema(py_type)
        properties[param_name] = prop_schema

        # Default yoksa required
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    # Docstring'ten basit ":param NAME: ..." satırlarını çekip parametrelere
    # description olarak ekleyebiliyoruz. Opsiyonel ama LLM'e yardımcı.
    doc = inspect.getdoc(fn) or ""
    for line in doc.splitlines():
        line = line.strip()
        if line.startswith(":param "):
            try:
                head, desc = line.split(":", 2)[1:]
                pname = head.replace("param", "").strip()
                if pname in properties and desc.strip():
                    properties[pname]["description"] = desc.strip()
            except Exception:
                pass

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }
    if required:
        schema["required"] = required
    return schema


def _py_type_to_json_schema(py_type: Any) -> dict[str, Any]:
    """Python tip ipucundan JSON schema parçası üret. Geniş bir alt küme destekler."""
    # Doğrudan eşleşme
    if py_type in _PRIMITIVE_MAP:
        return dict(_PRIMITIVE_MAP[py_type])

    origin = typing.get_origin(py_type)
    args = typing.get_args(py_type)

    # Optional[X] / Union[X, None] -> X (None düş)
    if origin is typing.Union or (origin is not None and getattr(py_type, "__class__", None).__name__ == "UnionType"):
        non_none = [a for a in args if a is not type(None)]  # noqa: E721
        if len(non_none) == 1:
            return _py_type_to_json_schema(non_none[0])
        # Birden çok tip: anyOf
        return {"anyOf": [_py_type_to_json_schema(a) for a in non_none]}

    # list[X] / List[X]
    if origin in (list,) or py_type is list:
        if args:
            return {"type": "array", "items": _py_type_to_json_schema(args[0])}
        return {"type": "array"}

    # tuple[X, ...]
    if origin in (tuple,):
        if args and len(args) == 2 and args[1] is Ellipsis:
            return {"type": "array", "items": _py_type_to_json_schema(args[0])}
        if args:
            return {
                "type": "array",
                "prefixItems": [_py_type_to_json_schema(a) for a in args],
            }
        return {"type": "array"}

    # dict[K, V] / Dict[...]
    if origin in (dict,) or py_type is dict:
        if args and len(args) == 2:
            return {"type": "object", "additionalProperties": _py_type_to_json_schema(args[1])}
        return {"type": "object"}

    # Literal["a", "b"]
    if origin is typing.Literal:
        if args and all(isinstance(a, str) for a in args):
            return {"type": "string", "enum": list(args)}
        if args and all(isinstance(a, int) for a in args):
            return {"type": "integer", "enum": list(args)}
        return {"enum": list(args)}

    # Any
    if py_type is typing.Any or py_type is Any:
        return {}

    # Class with __name__ logging için
    name = getattr(py_type, "__name__", str(py_type))
    logger.debug("Bilinmeyen tip '%s' -> string fallback", name)
    return {"type": "string"}


# ----------------------------------------------------------- format adapters


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


def get_collisions() -> dict[str, list[str]]:
    """Tool names registered by more than one module (name -> modules, in order).

    Empty when every @tool name is unique. A non-empty result means last-import
    silently shadows an earlier definition — see tests/test_no_tool_collisions.py.
    """
    return {k: list(v) for k, v in _COLLISIONS.items()}


def clear_registry() -> None:
    """Test/yeniden yükleme için registry'i sıfırla."""
    _REGISTRY.clear()
    _COLLISIONS.clear()
