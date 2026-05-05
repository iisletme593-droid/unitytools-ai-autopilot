# Migration From V1

V2 keeps the original idea but changes the center of gravity.

## Main Changes

| V1 | V2 |
| --- | --- |
| C#-heavy bridge experiments | Python core with small Unity Editor bridge |
| Terminal-first chat | Native Unity Editor AI panel |
| Anthropic-only direction | Ollama local-first, Anthropic optional |
| Manual bridge copy | `unitytools install-unity-plugin` helper |
| External terminal chat server | Silent embedded chat core started by the panel |

## Preserved Ideas

- Unity scene automation.
- Blender headless export scripts.
- Pipeline tools that combine Blender and Unity.
- Scene/profile/vision concepts for future ports.

## What To Port Next

- Vision scoring from V1.
- Scene profile loader.
- Persistent disk-backed task queue.
- More Unity command handlers.
- UI Toolkit version of the current IMGUI panel.

## Recommended Path

1. Use V2 with Ollama locally.
2. Add Unity command handlers one by one.
3. Port Blender/vision tools as Python `@tool` functions.
4. Keep Unity C# thin: transport and Editor API only.
