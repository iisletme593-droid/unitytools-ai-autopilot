"""Pipeline tool'ları: Blender + Unity birleştiren composite işlemler."""
from __future__ import annotations

from pathlib import Path

from ..core.tool_registry import tool

_BLENDER = None  # type: ignore
_UNITY = None  # type: ignore


@tool(
    description=(
        "Tek seferde: Blender'dan FBX export et + Unity'ye import et. "
        "blend_file: kaynak. unity_assets_relative: 'Models/Hero.fbx' gibi Unity Assets'a göre."
    )
)
def pipeline_blend_to_unity(
    blend_file: str,
    unity_assets_relative: str,
    slot: str = "",
    scale: float = 1.0,
) -> dict:
    if _BLENDER is None or _UNITY is None:
        return {"ok": False, "error": "Bridge'ler initialize edilmedi"}

    blend = Path(blend_file)
    if not blend.exists():
        return {"ok": False, "error": f".blend yok: {blend}"}

    # 1. Geçici klasöre export
    import tempfile
    tmp_dir = Path(tempfile.gettempdir()) / "unitytools_export"
    tmp_dir.mkdir(exist_ok=True)
    tmp_fbx = tmp_dir / (Path(unity_assets_relative).stem + ".fbx")

    export_result = _BLENDER.export_fbx(
        blend_file=blend, output_path=tmp_fbx, slot=slot or None, scale=scale
    )
    if not export_result.success:
        return {
            "ok": False,
            "stage": "blender_export",
            "error": export_result.stderr[-500:],
        }

    # 2. Unity'ye import
    if not _UNITY.is_connected():
        return {
            "ok": False,
            "stage": "unity_import",
            "error": "Unity Editor açık değil veya bridge çalışmıyor",
            "fbx_path": str(tmp_fbx),
        }

    try:
        import_result = _UNITY.call(
            "import_asset",
            {"src_path": str(tmp_fbx), "dst_relative": unity_assets_relative},
        )
        return {
            "ok": True,
            "fbx_size_bytes": tmp_fbx.stat().st_size,
            "unity_path": import_result.get("dst_path") if isinstance(import_result, dict) else None,
        }
    except Exception as e:
        return {"ok": False, "stage": "unity_import", "error": str(e), "fbx_path": str(tmp_fbx)}
