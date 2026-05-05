"""Blender ile ilgili tool'lar. Claude bunları çağırır."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..core.tool_registry import tool

# Bridge inject edilir (tools/__init__.py)
_BLENDER = None  # type: ignore


@tool(
    description=(
        "Bir .blend dosyasından FBX export et. Eğer 'slot' verilirse sadece "
        "ismi slot adını içeren objeleri export eder, yoksa tüm scene'i export eder."
    )
)
def blender_export_fbx(
    blend_file: str,
    output_path: str,
    slot: str = "",
    scale: float = 1.0,
) -> dict:
    """blend_file: kaynak .blend dosyası. output_path: hedef .fbx dosyası."""
    if _BLENDER is None:
        return {"ok": False, "error": "BlenderBridge initialize edilmedi"}

    blend = Path(blend_file)
    if not blend.exists():
        return {"ok": False, "error": f".blend bulunamadı: {blend}"}

    # Output klasörünü garantile
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    result = _BLENDER.export_fbx(
        blend_file=blend,
        output_path=out,
        slot=slot or None,
        scale=scale,
    )

    return {
        "ok": result.success,
        "output_path": str(out) if result.success else None,
        "stderr": result.stderr[-500:] if result.stderr else "",
        "size_bytes": out.stat().st_size if out.exists() else 0,
    }


@tool(description="Bir .blend dosyasındaki tüm objeleri listele.")
def blender_list_objects(blend_file: str) -> dict:
    if _BLENDER is None:
        return {"ok": False, "error": "BlenderBridge initialize edilmedi"}

    blend = Path(blend_file)
    if not blend.exists():
        return {"ok": False, "error": f".blend bulunamadı: {blend}"}

    # Inline Python script — bpy ile listele, stdout'a yazdır
    script_content = (
        "import bpy, json\n"
        "objs = [{'name': o.name, 'type': o.type} for o in bpy.data.objects]\n"
        "print('OBJECTS_JSON_BEGIN'); print(json.dumps(objs)); print('OBJECTS_JSON_END')\n"
    )
    # Geçici script yaz
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(script_content)
        tmp_script = f.name

    try:
        result = _BLENDER.run_script(tmp_script, blend_file=blend)
        if not result.success:
            return {"ok": False, "error": result.stderr[-500:]}

        # stdout'tan JSON'u çıkar
        out = result.stdout
        start = out.find("OBJECTS_JSON_BEGIN")
        end = out.find("OBJECTS_JSON_END")
        if start == -1 or end == -1:
            return {"ok": False, "error": "Çıktı parse edilemedi"}
        import json as _json
        json_str = out[start + len("OBJECTS_JSON_BEGIN") : end].strip()
        objects = _json.loads(json_str)
        return {"ok": True, "objects": objects, "count": len(objects)}
    finally:
        Path(tmp_script).unlink(missing_ok=True)
