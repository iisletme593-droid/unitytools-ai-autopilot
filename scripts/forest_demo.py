"""Live demo: one-command optimized forest -> visual QA -> quality loop.

Snapshots the current scene first (restorable), then generates a small forest,
QA's it, and runs the auto-fix quality pass. Leaves the forest in the editor so
you can look at it; prints the snapshot path so SampleScene can be restored.
Run: .venv/Scripts/python.exe scripts/forest_demo.py
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


def show(title, obj, limit=1800):
    print(f"\n--- {title} ---")
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=2)
    except Exception:
        text = repr(obj)
    print(text[:limit])


def main() -> int:
    cfg = Config.load(PROJECT)
    bridge = UnityBridge(cfg)
    init_tools(None, bridge)
    if not bridge.connect(timeout=2.0):
        print("BRIDGE NOT REACHABLE")
        return 2
    print("connect: OK | port:", cfg.unity_bridge_port)

    snap = ut.unity_create_scene_snapshot(label="before_forest_demo")
    show("1) snapshot (restore point)", snap)

    show("2) create_optimized_forest_scene (40 trees, 80m terrain)",
         ut.unity_create_optimized_forest_scene(clear_scene=True, tree_count=40, rock_count=8, terrain_size=80.0, seed=7))

    show("3) run_visual_qa", ut.unity_run_visual_qa(capture_screenshot=True))

    show("4) quality_pass (auto_fix=True)", ut.unity_quality_pass(auto_fix=True, max_passes=2, capture_screenshot=False))

    path = snap.get("snapshot_path") if isinstance(snap, dict) else None
    print("\nDONE. Forest left in the editor for you to view.")
    print("Restore SampleScene anytime with:")
    print(f'  unity_restore_scene_snapshot("{path}")')
    return 0


if __name__ == "__main__":
    sys.exit(main())
