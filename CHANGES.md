# UnityTools V2 Changes

## Current hotfix

- Fixed terminal chat startup (`model_label` was undefined).
- Reinstalled the editable Python package so `unitytools.exe` points at this checkout.
- Added bounded Unity scene listing to avoid large-scene RPC timeouts.
- Added `find_scene_objects` RPC/tool so search no longer requires dumping the whole scene.
- Hardened the Unity bridge across assembly reloads and editor quit.
- Updated the embedded Unity panel/core flow for local Ollama operation.
- Added a `hello` handshake from the chat server so the panel can show provider/model/tool count.
- Updated tests to validate the new `hello -> ping/pong -> tool flow` protocol.
- Added procedural Unity tools for grids, circles, scatter, walls, and stairs.

## Unity project cleanup performed locally

- Fixed missing Autopilot processor classes with safe placeholder executors.
- Fixed `SceneBuilder` null-coalescing statement compile error.
- Removed obsolete `FindObjectsSortMode` usages in project scripts.
- Fixed unused-field warnings in gameplay scripts.
- Added Unity import maintenance scripts to clean model import settings and clear Console.
- Quarantined known broken GLB imports under `AutopilotData/QuarantinedBrokenImports`.

## Verification

- `python -m compileall unitytools tests` passes.
- `tests/test_chat_server.py` passes.
- `unitytools doctor` reports Ollama, Unity bridge, and Blender OK.
- Real Ollama tool-call test successfully called `unity_list_scene_objects(max_count=5)` without timeout.
