"""Config yükleme: .env + config.yaml + environment variables."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class Config:
    """Çalışma zamanı yapılandırması."""

    # Anthropic API
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    provider: str = "ollama"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"

    # Bridge ayarları
    unity_bridge_port: int = 7777
    unity_bridge_host: str = "127.0.0.1"

    # Executable yolları
    blender_executable: Optional[str] = None
    unity_executable: Optional[str] = None

    # Proje
    project_root: Path = field(default_factory=lambda: Path.cwd())

    # Logging
    log_level: str = "INFO"

    @classmethod
    def load(cls, project_root: Optional[Path] = None) -> "Config":
        """`.env` ve environment'tan config oluştur.

        project_root verilmediyse cwd kullanır.
        """
        root = project_root or Path.cwd()
        env_path = root / ".env"
        if env_path.exists():
            load_dotenv(env_path)

        cfg = cls(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            model=os.getenv("UNITYTOOLS_MODEL", "claude-sonnet-4-20250514"),
            provider=os.getenv("UNITYTOOLS_PROVIDER", "ollama").lower(),
            ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            unity_bridge_port=int(os.getenv("UNITY_BRIDGE_PORT", "7777")),
            unity_bridge_host=os.getenv("UNITY_BRIDGE_HOST", "127.0.0.1"),
            blender_executable=os.getenv("BLENDER_EXECUTABLE") or _autodetect_blender(),
            unity_executable=os.getenv("UNITY_EXECUTABLE"),
            project_root=root,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
        return cfg

    def validate(self) -> list[str]:
        """Eksik/hatal? ayarlar? liste olarak d?nd?r."""
        problems: list[str] = []
        if self.provider not in {"anthropic", "ollama"}:
            problems.append("UNITYTOOLS_PROVIDER 'anthropic' veya 'ollama' olmali.")
        if self.provider == "anthropic":
            if not self.api_key:
                problems.append("ANTHROPIC_API_KEY .env dosyas?nda veya environment'ta yok.")
            elif not self.api_key.startswith("sk-ant-"):
                problems.append(
                    "ANTHROPIC_API_KEY mevcut ama Anthropic API anahtari gibi gorunmuyor "
                    "(beklenen prefix: sk-ant-)."
                )
        if self.provider == "ollama" and not self.ollama_model:
            problems.append("OLLAMA_MODEL bos olamaz.")
        if not self.blender_executable:
            problems.append(
                "Blender bulunamad?. .env'de BLENDER_EXECUTABLE'? set et veya "
                "blender'? PATH'e ekle."
            )
        elif not Path(self.blender_executable).exists():
            problems.append(f"BLENDER_EXECUTABLE yolu mevcut de?il: {self.blender_executable}")
        return problems


def _autodetect_blender() -> Optional[str]:
    """PATH'te ve standart konumlarda Blender'ı ara."""
    # PATH
    found = shutil.which("blender")
    if found:
        return found

    # Windows standart konumları
    candidates = [
        Path("C:/Program Files/Blender Foundation"),
        Path("C:/Program Files (x86)/Blender Foundation"),
    ]
    for base in candidates:
        if not base.exists():
            continue
        # En yeni sürümü bul
        versions = sorted(base.glob("Blender*"), reverse=True)
        for v in versions:
            exe = v / "blender.exe"
            if exe.exists():
                return str(exe)

    # macOS
    mac_path = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    if mac_path.exists():
        return str(mac_path)

    return None
