# Integration status — is the chat → Unity game path actually wired?

Honest answer: **the whole pipeline is wired and protocol-consistent, and it is now covered
by in-process end-to-end tests. The one thing automated tests cannot do is render a real
frame — that step needs a live Unity Editor, and you run it with one command (below).**

This document is the source of truth for "does it really work, end to end".

## The layers (all present in this repo)

| Layer | Where | Role |
|-------|-------|------|
| Editor chat UI | `unity_plugin/Editor/Bridge/ChatWindow.cs` | The in-Unity chat panel you type into |
| Editor bridge server | `unity_plugin/Editor/Bridge/BridgeServer.cs` | TCP listener inside Unity (port 7777–7800) |
| Editor command handlers | `unity_plugin/Editor/Bridge/CommandHandlers.cs` | Executes each RPC (`create_primitive`, `add_component`, …) |
| Chat server launcher | `unity_plugin/Editor/Bridge/ChatServerProcess.cs` | Starts the Python chat server from the editor |
| Chat server | `unitytools/core/chat_server.py` | TCP server; auth + routes each message |
| Fast path | `unitytools/core/game_studio_actions.py` | Deterministic NL → tool steps (no LLM) |
| LLM brain | `unitytools/core/orchestrator.py` (+ `model_router`, `dual_agent`) | Tool-calling loop for novel requests |
| Tool registry | `unitytools/core/tool_registry.py` | `@tool` → JSON schema; 120+ tools |
| Unity bridge client | `unitytools/bridges/unity.py` | Python → editor JSON-RPC over TCP |
| Game studio core | `core/game_blueprint.py`, `core/gameplay.py`, `core/game_qa.py` | Plans + generates + self-audits games |
| CLI | `unitytools/cli/entry.py` | Launches the chat / bridge servers |

## What is PROVEN in CI (no Unity needed)

- **Protocol parity** — `tests/test_bridge_protocol_parity.py` reads the C# command vocabulary
  straight out of `CommandHandlers.cs` and asserts **every** RPC method the Python game-build
  path emits is one the editor actually handles. If a change makes Python call a method the
  editor can't answer (the exact thing that silently breaks a live build), CI goes red.
  - The game-build path emits only: `create_primitive`, `set_tag`, `import_asset`,
    `get_editor_state`, `add_component`, `add_collider`, `get_object_details` — all handled by C#.
  - `place_primitives` is explicitly **not** a bridge method: `unity_place_primitives` loops
    `create_primitive` (which C# handles), guarded by a regression test.
- **End-to-end build sequence** — `tests/test_game_build_integration.py` runs
  `unity_build_simple_game(execute=True)` for **all 17 game types** + composed games against a
  recording fake bridge and asserts the real phase order: geometry → import each UNIQUE script
  once → poll `get_editor_state` until compiled → attach a component per object.
- **The whole chat loop** — a natural-language string (`"boss arena oyunu kur ve uygula"`) drives
  a real build through `run_unity_fast_action`; the same string without the opt-in builds nothing.
- 1480+ unit tests on the planning / QA / intent layers (every game type valid + playable +
  coherent; every example prompt routes to its own build).

## What still needs a LIVE Unity (you run it)

Rendering an actual scene and pressing Play. Two one-command checks against your editor:

```
set UNITY_PROJECT_ROOT=C:\path\to\YourUnityProject
.venv/Scripts/python.exe scripts/live_check.py            # read-only: ping, scene, QA, snapshot
.venv/Scripts/python.exe scripts/build_check.py boss 4    # BUILDS a real game in the open scene
```

`build_check.py` snapshots first, then creates the geometry, imports the C# behaviours
(triggering a recompile), waits, and attaches the components — i.e. the full chat→game path,
live. Then press **Play** in Unity.

## How "chatting like this" maps to a real build

1. Type in the editor's UnityTools chat panel (or send to the chat server).
2. The fast path turns `"boss oyunu kur"` into a **plan** (safe, no scene change by default).
3. Add an explicit opt-in to actually build it: **`"boss oyunu kur ve uygula"`** /
   `"build and apply"` / `"sahneye uygula"` → `execute=True`, and the bridge builds it live.
   (Without the opt-in it only plans — so nothing mutates your scene by accident.)
4. For anything the fast path doesn't recognize, the LLM brain picks tools and can build the
   same way.

## Setup checklist

1. Copy `unity_plugin/` into your Unity project's `Assets/` (or install the package). Open the
   **UnityTools AI** panel — this starts `BridgeServer` (and can launch the Python chat server).
2. Put a `.env` in the Unity project root with the bridge token + LLM provider/key
   (`ANTHROPIC_API_KEY`, or `OLLAMA_MODEL`, or Cloudflare creds). See `docs/CLOUD_SETUP_UNITY.md`.
3. `pip install -e .` (or use the bundled `.venv`).
4. Run `scripts/live_check.py` (connectivity) then `scripts/build_check.py` (a real build).
