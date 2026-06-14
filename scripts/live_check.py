"""Live end-to-end check against a running Unity Editor bridge.

SAFE: connects, reads the current scene, takes a protective snapshot, and runs
visual-QA + a report-only quality pass. Does NOT delete or regenerate the scene.
Run: .venv/Scripts/python.exe scripts/live_check.py
"""
import json
import os
import sys
from pathlib import Path

from unitytools.core.config import Config
from unitytools.bridges.unity import UnityBridge
from unitytools.tools import init_tools
import unitytools.tools.unity_tools as ut

# Point at the Unity project that holds the bridge .env (token + port).
PROJECT = Path(os.getenv("UNITY_PROJECT_ROOT", r"C:\Users\i97452402\My project"))


def show(title, obj, limit=1600):
    print(f"\n--- {title} ---")
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        text = repr(obj)
    print(text[:limit])


def main() -> int:
    if not (PROJECT / ".env").exists():
        print(f"Unity proje .env bulunamadi: {PROJECT}\\.env")
        return 3

    cfg = Config.load(PROJECT)
    print("provider:", cfg.provider, "| host:", cfg.unity_bridge_host, "| port:", cfg.unity_bridge_port)
    print("token:", f"set (len={len(cfg.bridge_token)})" if cfg.bridge_token else "MISSING")

    bridge = UnityBridge(cfg)
    init_tools(None, bridge)

    if not bridge.connect(timeout=2.0):
        print("\nBRIDGE NOT REACHABLE: Unity Editor acik mi? 'UnityTools AI' paneli (BridgeServer) calisiyor mu?")
        return 2
    print("connect: OK | port:", cfg.unity_bridge_port)

    show("1) ping", ut.unity_ping())

    es = ut.unity_get_editor_state()
    show("2) editor_state", es)

    cat = ut.unity_get_scene_catalog(max_results=20)
    if isinstance(cat, dict):
        show("3) scene_catalog (ozet)", {k: cat.get(k) for k in ("ok", "scene", "total_objects", "returned", "groups")})
    else:
        show("3) scene_catalog", cat)

    show("4) protective snapshot", ut.unity_create_scene_snapshot(label="live_check_before"))

    show("5) run_visual_qa", ut.unity_run_visual_qa(capture_screenshot=True))

    show("6) quality_pass (REPORT-ONLY, no mutation)", ut.unity_quality_pass(auto_fix=False, capture_screenshot=False))

    print("\nLIVE CHECK DONE (no destructive action taken)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
