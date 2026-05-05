"""Config yükleme: .env + environment variables."""
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

    # LLM provider
    api_key: str = ""
    model: str = "claude-sonnet-4-20250514"
    provider: str = "ollama"  # "anthropic" | "ollama"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"

    # Üretim parametreleri
    max_tokens: int = 8192
    history_turn_limit: int = 40

    # Bridge ayarları
    unity_bridge_port: int = 7777
    unity_bridge_host: str = "127.0.0.1"
    unity_rpc_timeout: float = 180.0

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
            max_tokens=_int_env("UNITYTOOLS_MAX_TOKENS", 8192),
            history_turn_limit=_int_env("UNITYTOOLS_HISTORY_LIMIT", 40),
            unity_bridge_port=_int_env("UNITY_BRIDGE_PORT", 7777),
            unity_bridge_host=os.getenv("UNITY_BRIDGE_HOST", "127.0.0.1"),
            unity_rpc_timeout=_float_env("UNITY_RPC_TIMEOUT", 180.0),
            blender_executable=os.getenv("BLENDER_EXECUTABLE") or _autodetect_blender(),
            unity_executable=os.getenv("UNITY_EXECUTABLE"),
            project_root=root,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
        return cfg

    def validate(self) -> list[str]:
        """Eksik/hatalı ayarları liste olarak döndür."""
        problems: list[str] = []
        if self.provider not in {"anthropic", "ollama"}:
            problems.append(
                f"UNITYTOOLS_PROVIDER 'anthropic' veya 'ollama' olmali (suanki: {self.provider!r})."
            )
        if self.provider == "anthropic":
            if not self.api_key:
                problems.append(
                    "ANTHROPIC_API_KEY .env dosyasinda veya environment'ta yok."
                )
            elif not self.api_key.startswith("sk-ant-"):
                problems.append(
                    "ANTHROPIC_API_KEY mevcut ama Anthropic API anahtari gibi gorunmuyor "
                    "(beklenen prefix: sk-ant-)."
                )
        if self.provider == "ollama" and not self.ollama_model:
            problems.append("OLLAMA_MODEL bos olamaz.")
        if self.provider == "ollama":
            # Bilinen küçük modeller için uyarı
            risky = ("qwen3:1b", "qwen3:4b", "llama3.2:1b", "llama3.2:3b", "phi3:mini")
            if any(self.ollama_model.startswith(r) for r in risky):
                problems.append(
                    f"OLLAMA_MODEL='{self.ollama_model}' tool calling icin guvenilir degildir. "
                    f"Onerilen: qwen2.5:7b-instruct, llama3.1:8b, ya da daha buyuk."
                )
        if not self.blender_executable:
            problems.append(
                "Blender bulunamadi. .env'de BLENDER_EXECUTABLE'i set et veya "
                "blender'i PATH'e ekle."
            )
        elif not Path(self.blender_executable).exists():
            problems.append(
                f"BLENDER_EXECUTABLE yolu mevcut degil: {self.blender_executable}"
            )
        if self.max_tokens < 512:
            problems.append("UNITYTOOLS_MAX_TOKENS cok dusuk (<512).")
        if self.history_turn_limit < 4:
            problems.append("UNITYTOOLS_HISTORY_LIMIT cok dusuk (<4).")
        return problems


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _autodetect_blender() -> Optional[str]:
    """PATH'te ve standart konumlarda Blender'ı ara."""
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
