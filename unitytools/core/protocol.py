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


# Editor tarafının desteklediği method isimleri (sadece referans)
UNITY_METHODS = {
    "ping",
    "get_project_info",
    "list_scene_objects",
    "create_primitive",          # cube/sphere/...
    "set_transform",
    "set_material_color",
    "import_asset",              # FBX vs.'i Assets/'a kopyala + AssetDatabase.Refresh
    "instantiate_prefab",
    "save_scene",
    "open_scene",
    "execute_menu_item",         # "GameObject/3D Object/Cube" gibi
    "run_csharp_script",         # uzun vade için: Editor'de C# kod parçası çalıştır
}
