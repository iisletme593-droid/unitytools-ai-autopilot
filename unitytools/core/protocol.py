"""Python ↔ Unity Editor arası JSON-RPC mesaj formatı.

Tek satır JSON, satır sonu newline. Unity tarafı aynı formatı kullanır.
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RpcRequest(BaseModel):
    """Python'dan Unity'ye giden istek."""

    id: str
    method: str  # "create_cube", "import_fbx", "list_scene_objects" vs.
    params: dict[str, Any] = Field(default_factory=dict)
    # Paylasilan gizli token (UNITYTOOLS_SECRET/BRIDGE_TOKEN). Editor tarafi
    # yapilandirilmissa bunu sabit zamanli karsilastirir. None ise gonderilmez.
    token: Optional[str] = None


class RpcError(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None


class RpcResponse(BaseModel):
    """Unity'den dönen cevap."""

    id: str
    result: Optional[Any] = None
    error: Optional[RpcError] = None

    @property
    def ok(self) -> bool:
        return self.error is None


# NOTE: a stale UNITY_METHODS reference set used to live here. It was unused, listed
# a phantom "run_csharp_script" the editor never implements, and omitted ~40 real
# commands — so it could only mislead. The authoritative command list is the C#
# dispatch switch in unity_plugin/Editor/Bridge/CommandHandlers.cs.
