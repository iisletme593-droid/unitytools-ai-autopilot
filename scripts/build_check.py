"""Live END-TO-END build check against a running Unity Editor bridge.

Unlike scripts/live_check.py (which is read-only), this one BUILDS A REAL GAME in the
open scene: it connects, takes a protective snapshot, then runs
unity_build_simple_game(execute=True) -- creating the geometry, importing the behaviour
MonoBehaviours (which triggers a Unity recompile), waiting for the compile, and attaching
the components. This is the proof that "chat -> playable Unity game" works on your machine.

SAFE-ISH: it snapshots first (restore via the UnityTools panel or unity_restore_scene_snapshot),
and only builds into the active scene. Run with the Editor in focus (script import reloads
the domain).

Usage:
    set UNITY_PROJECT_ROOT=C:\\path\\to\\UnityProject   (the project that holds the bridge .env)
    .venv/Scripts/python.exe scripts/build_check.py [game_type] [count]
    e.g.  .venv/Scripts/python.exe scripts/build_check.py boss 4
"""
import json
import os
import sys
from pathlib import Path

from unitytools.core.config import Config
from unitytools.bridges.unity import UnityBridge
from unitytools.tools import init_tools
import unitytools.tools.unity_tools as ut
from unitytools.core.game_blueprint import BLUEPRINTS

PROJECT = Path(os.getenv("UNITY_PROJECT_ROOT", r"C:\Users\i97452402\My project"))


def show(title, obj, limit=2000):
    print(f"\n--- {title} ---")
    try:
        print(json.dumps(obj, ensure_ascii=False, indent=2)[:limit])
    except Exception:
        print(repr(obj)[:limit])


def main() -> int:
    game_type = sys.argv[1] if len(sys.argv) > 1 else "collectathon"
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    if game_type not in BLUEPRINTS:
        print(f"Bilinmeyen oyun turu: {game_type!r}. Mevcut: {', '.join(sorted(BLUEPRINTS))}")
        return 3

    if not (PROJECT / ".env").exists():
        print(f"Unity proje .env bulunamadi: {PROJECT}\\.env  (UNITY_PROJECT_ROOT'u ayarla)")
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
    show("2) protective snapshot", ut.unity_create_scene_snapshot(label="build_check_before"))

    print(f"\n>>> BUILDING a '{game_type}' game (count={count}) FOR REAL in the active scene...")
    print("    (this creates objects, imports C# behaviours -> a Unity recompile, then attaches them)")
    result = ut.unity_build_simple_game(collectible_count=count, execute=True, game_type=game_type)
    show("3) build result", result)

    applied = result.get("applied") or result.get("steps_applied") or []
    if isinstance(applied, list) and applied:
        ok = sum(1 for a in applied if a.get("ok"))
        print(f"\nApplied {ok}/{len(applied)} steps ok. unique_scripts={result.get('unique_scripts')}")

    if result.get("ok"):
        print("\nBUILD CHECK DONE: a playable game was assembled. Press Play in Unity to try it.")
        print("Restore the prior scene from the UnityTools panel (snapshot 'build_check_before') if needed.")
        return 0
    print("\nBUILD CHECK FAILED -- see the build result above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
