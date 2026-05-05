"""Blender bridge: subprocess ile `blender --background --python script.py` çalıştırır.

İki mod:
- Headless (one-shot): script çalış, kapan. FBX export gibi işler için.
- Persistent (gelecek özellik): blender'ı arka planda açık tut, TCP üzerinden komut yolla.
  Bu sürümde sadece headless mod var.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..core.config import Config

logger = logging.getLogger(__name__)


@dataclass
class BlenderResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int


class BlenderBridge:
    """Blender'a headless komut yollar."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.scripts_dir = Path(__file__).parent.parent.parent / "scripts" / "blender"

    def is_available(self) -> bool:
        return bool(self.config.blender_executable) and Path(self.config.blender_executable).exists()

    def run_script(
        self,
        script_path: Path | str,
        blend_file: Optional[Path | str] = None,
        script_args: Optional[list[str]] = None,
        timeout: int = 300,
    ) -> BlenderResult:
        """Blender'ı verilen script ile çalıştır.

        Args:
            script_path: Çalışacak Python dosyası (`scripts/blender/` altında)
            blend_file: Açılacak .blend dosyası (yoksa boş scene)
            script_args: Script'e geçecek argümanlar (`--` sonrası gönderilir)
            timeout: Saniye cinsinden zaman aşımı

        Dönen: BlenderResult
        """
        if not self.is_available():
            return BlenderResult(
                success=False,
                stdout="",
                stderr=f"Blender executable bulunamadı: {self.config.blender_executable}",
                return_code=-1,
            )

        cmd: list[str] = [self.config.blender_executable, "--background"]

        if blend_file:
            blend_path = Path(blend_file)
            if not blend_path.exists():
                return BlenderResult(
                    success=False, stdout="", stderr=f".blend dosyası yok: {blend_path}", return_code=-1
                )
            cmd.append(str(blend_path))

        cmd.extend(["--python", str(script_path)])

        if script_args:
            cmd.append("--")
            cmd.extend(script_args)

        logger.info("Blender çalıştırılıyor: %s", " ".join(cmd))

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return BlenderResult(
                success=proc.returncode == 0,
                stdout=proc.stdout,
                stderr=proc.stderr,
                return_code=proc.returncode,
            )
        except subprocess.TimeoutExpired:
            return BlenderResult(
                success=False,
                stdout="",
                stderr=f"Blender {timeout} saniyede bitmedi (timeout)",
                return_code=-2,
            )
        except FileNotFoundError as e:
            return BlenderResult(
                success=False, stdout="", stderr=f"Blender çalıştırılamadı: {e}", return_code=-3
            )

    def export_fbx(
        self,
        blend_file: Path | str,
        output_path: Path | str,
        slot: Optional[str] = None,
        scale: float = 1.0,
    ) -> BlenderResult:
        """`scripts/blender/export_fbx.py` script'ini kullanarak FBX export."""
        script = self.scripts_dir / "export_fbx.py"
        if not script.exists():
            return BlenderResult(
                success=False, stdout="", stderr=f"Export script yok: {script}", return_code=-1
            )

        args = [str(output_path)]
        if slot:
            args.extend(["--slot", slot])
        if scale != 1.0:
            args.extend(["--scale", str(scale)])

        return self.run_script(script, blend_file=blend_file, script_args=args)
