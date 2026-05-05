"""Editor ↔ Python chat protokolü.

Newline-delimited JSON. İki yönlü.

Editor → Python:
    {"type":"user_message","content":"merhaba"}
    {"type":"reset"}                          # geçmişi sıfırla
    {"type":"ping"}

Python → Editor:
    {"type":"thinking"}                                    # düşünüyor (UI spinner)
    {"type":"tool_call","tool":"create_primitive","input":{...}}
    {"type":"tool_result","tool":"create_primitive","ok":true,"result":{...}}
    {"type":"assistant_text","content":"...","done":false}  # streaming chunk
    {"type":"assistant_done","stop_reason":"end_turn"}     # tur bitti
    {"type":"error","message":"..."}
    {"type":"pong"}
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


# Editor → Python
class UserMessage(BaseModel):
    type: str = "user_message"
    content: str


class Reset(BaseModel):
    type: str = "reset"


class Ping(BaseModel):
    type: str = "ping"


# Python → Editor
class Thinking(BaseModel):
    type: str = "thinking"


class ToolCall(BaseModel):
    type: str = "tool_call"
    tool: str
    input: dict[str, Any]


class ToolResult(BaseModel):
    type: str = "tool_result"
    tool: str
    ok: bool
    result: Any = None
    error: Optional[str] = None


class AssistantText(BaseModel):
    type: str = "assistant_text"
    content: str
    done: bool = False


class AssistantDone(BaseModel):
    type: str = "assistant_done"
    stop_reason: str = "end_turn"


class ErrorMessage(BaseModel):
    type: str = "error"
    message: str


class Pong(BaseModel):
    type: str = "pong"
