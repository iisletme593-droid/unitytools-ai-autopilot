"""Paylasilan guvenlik yardimcilari.

Chat server ve Unity/Unreal kopruleri ayni surec/makine icindeki baglantilari
dogrulamak ve dosya islemlerini sinirlamak icin bu modulu kullanir:

* `get_bridge_token` / `tokens_match` - paylasilan gizli token (sabit zamanli
  karsilastirma). Token `UNITYTOOLS_BRIDGE_TOKEN` -> `UNITYTOOLS_SECRET` ->
  `UNITYTOOLS_KEY` sirasiyla cozulur. Bos token "auth kapali" demektir.
* `is_loopback_host` / `is_loopback_addr` - dinleyici/baglanti adresinin sadece
  loopback olmasini zorlamak icin.
* `safe_contained_path` - bir koke gore yol cozumler; `..`, mutlak yol veya
  surucu harfiyle disari kacisi reddeder (path traversal korumasi).
"""
from __future__ import annotations

import hmac
import ipaddress
import os
import socket
from pathlib import Path
from typing import Optional

_TRUTHY = {"1", "true", "yes", "on"}


def get_bridge_token(explicit: Optional[str] = None) -> str:
    """Paylasilan kopru/chat token'ini config veya environment'tan coz.

    Oncelik: acik deger -> UNITYTOOLS_BRIDGE_TOKEN -> UNITYTOOLS_SECRET ->
    UNITYTOOLS_KEY. Bos string "auth ayarlanmamis" anlamina gelir.
    """
    candidates = (
        explicit,
        os.getenv("UNITYTOOLS_BRIDGE_TOKEN"),
        os.getenv("UNITYTOOLS_SECRET"),
        os.getenv("UNITYTOOLS_KEY"),
    )
    for value in candidates:
        if value and value.strip():
            return value.strip()
    return ""


def tokens_match(expected: str, provided: Optional[str]) -> bool:
    """Sabit zamanli token karsilastirmasi.

    `expected` bos ise (auth yapilandirilmamis) her zaman True doner; aksi halde
    `provided` tam esleser olmali.
    """
    if not expected:
        return True
    if not provided:
        return False
    return hmac.compare_digest(str(expected), str(provided))


def allow_remote_enabled(explicit: Optional[bool] = None) -> bool:
    """Loopback disi baglanti acikca etkinlestirilmis mi?"""
    if explicit is not None:
        return bool(explicit)
    return os.getenv("UNITYTOOLS_ALLOW_REMOTE", "").strip().lower() in _TRUTHY


def is_loopback_host(host: Optional[str]) -> bool:
    """host loopback literal mi ya da yalnizca loopback adreslere mi cozuluyor."""
    if not host:
        return False
    h = host.strip()
    if h.lower() in ("localhost", "ip6-localhost", "ip6-loopback"):
        return True
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(h, None)
    except socket.gaierror:
        return False
    if not infos:
        return False
    for info in infos:
        ip = info[4][0]
        try:
            if not ipaddress.ip_address(ip).is_loopback:
                return False
        except ValueError:
            return False
    return True


def is_loopback_addr(addr: Optional[str]) -> bool:
    """Kabul edilen bir peer IP'sinin loopback olup olmadigini dogrula."""
    if not addr:
        return False
    try:
        return ipaddress.ip_address(addr).is_loopback
    except ValueError:
        return False


def safe_contained_path(root: "Path | str", relative: str) -> Path:
    """`relative` yolunu `root` altinda coz; disari kacarsa ValueError firlat.

    Mutlak yollari, surucu harfli yollari (C:\\...) ve `root` disina cikan `..`
    gezinmesini reddeder. Donen yol her zaman `root` icindedir.
    """
    root_path = Path(root).resolve()
    rel = str(relative or "").strip()
    if not rel:
        raise ValueError("bos yol")
    rel = rel.replace("\\", "/")
    candidate = Path(rel)
    # Mutlak ya da surucu-harfli ("C:/...") yollar yasak.
    if candidate.is_absolute() or (len(rel) >= 2 and rel[1] == ":"):
        raise ValueError(f"mutlak yol izinli degil: {relative!r}")
    full = (root_path / candidate).resolve()
    try:
        full.relative_to(root_path)
    except ValueError as exc:
        raise ValueError(f"yol {root_path} disina cikiyor: {relative!r}") from exc
    return full
