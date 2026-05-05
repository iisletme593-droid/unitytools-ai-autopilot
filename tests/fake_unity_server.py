"""Test için sahte Unity Editor TCP server'ı.
Gerçek Unity Editor'ün C# kodunun yapması gerekenleri Python'da simüle eder.

Çalıştır: python tests/fake_unity_server.py
"""
from __future__ import annotations

import json
import socket
import threading
from datetime import datetime


def handle_request(method: str, params: dict) -> dict:
    """Fake handler — gerçek Unity'nin döneceği şekilde cevap üret."""
    if method == "ping":
        return {"pong": True, "unity_version": "FAKE-6000.0", "time": datetime.utcnow().isoformat()}
    if method == "get_project_info":
        return {"project_name": "FakeProject", "unity_version": "FAKE-6000.0"}
    if method == "list_scene_objects":
        return {
            "scene": "SampleScene",
            "objects": [
                {"name": "Main Camera", "depth": 0, "active": True},
                {"name": "Directional Light", "depth": 0, "active": True},
            ],
            "count": 2,
        }
    if method == "create_primitive":
        return {"name": params.get("name", "Cube"), "instance_id": 12345}
    raise ValueError(f"Fake server: bilinmeyen method {method}")


def serve_client(conn: socket.socket, addr) -> None:
    print(f"[fake_unity] bağlantı: {addr}")
    buffer = b""
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, _, buffer = buffer.partition(b"\n")
                if not line.strip():
                    continue
                try:
                    req = json.loads(line.decode("utf-8"))
                    print(f"[fake_unity] ← {req}")
                    resp: dict
                    try:
                        result = handle_request(req["method"], req.get("params", {}))
                        resp = {"id": req["id"], "result": result}
                    except Exception as e:
                        resp = {"id": req["id"], "error": {"code": 1, "message": str(e)}}
                    out = json.dumps(resp).encode("utf-8") + b"\n"
                    conn.sendall(out)
                    print(f"[fake_unity] → {resp}")
                except Exception as e:
                    print(f"[fake_unity] parse hatası: {e}")
    finally:
        conn.close()
        print(f"[fake_unity] kapandı: {addr}")


def main() -> None:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 7777))
    s.listen(5)
    print("[fake_unity] dinliyor: 127.0.0.1:7777")
    try:
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=serve_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[fake_unity] kapatılıyor")
    finally:
        s.close()


if __name__ == "__main__":
    main()
