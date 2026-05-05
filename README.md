# UnityTools AI Autopilot

UnityTools AI Autopilot is a local-first AI panel for the Unity Editor. It lets you chat inside Unity and lets the model call real Unity and Blender tools: create scene objects, search and place real project assets, list the active scene, import assets, export FBX files from Blender, and run pipeline steps.

The default setup uses Ollama with `qwen3:4b`, so it can run without a paid API key. Anthropic Claude is still supported for users who want a stronger cloud model.

## Highlights

- Native Unity Editor panel: `Window > UnityTools AI > Autopilot Chat`
- No terminal needed during normal use: the panel starts the Python chat core silently
- Local/free model path with Ollama and `qwen3:4b`
- Optional Anthropic provider for higher quality reasoning
- Tool calling into Unity Editor over localhost TCP
- Semantic Unity asset catalogue: finds real assets even from fuzzy prompts like `real relis realist tree`
- Batch placement tools for forests, rock fields, prop clusters, asset grids, lines, and rings
- Blender headless bridge for `.blend` to `.fbx` export workflows
- Undo-aware Unity commands for created objects and transform changes
- GitHub-ready MIT licensed project

## What It Can Do

Try prompts like:

```text
Create 5 cubes along the X axis and name them TestCube_0 to TestCube_4.
Find realistic tree assets and group them by category.
Put 12 realistic trees from my assets around the scene.
Make a small forest using my real tree assets, not cubes.
Create a rock field from real boulder assets.
List all active scene objects.
Move Ollama_ChatServer_Cube to x=4 y=1 z=0.
Export Barbar.blend to FBX and import it into Assets/Models.
```

## Architecture

```text
Unity Editor AI Panel
  -> TCP 7778 -> Python chat core / orchestrator
  -> tool calls -> Unity bridge TCP 7777
  -> optional subprocess -> Blender headless scripts
```

Two local ports are used:

- `7777`: Python to Unity command bridge
- `7778`: Unity panel to Python chat core

Everything runs on `127.0.0.1`.

## Quick Start: Local Ollama Mode

1. Install Ollama:

```powershell
winget install --id Ollama.Ollama -e
```

2. Pull the recommended local model:

```powershell
ollama pull qwen3:4b
```

3. Install the Python package from this repository:

```powershell
pip install -e .
copy .env.example .env
```

4. Make sure `.env` uses Ollama:

```env
UNITYTOOLS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3:4b
```

5. Install the Unity Editor bridge into your Unity project:

```powershell
unitytools install-unity-plugin --project "C:\Path\To\YourUnityProject"
```

6. Open Unity and launch:

```text
Window > UnityTools AI > Autopilot Chat
```

The panel starts the Python chat core in the background. No external terminal window is required.

## Optional: Anthropic Mode

If you prefer Claude, set:

```env
UNITYTOOLS_PROVIDER=anthropic
ANTHROPIC_API_KEY=<your-anthropic-api-key>
UNITYTOOLS_MODEL=claude-sonnet-4-20250514
```

## Diagnostics

```powershell
unitytools doctor
unitytools status
unitytools unity-ping
```

`doctor` checks Ollama, the selected model, Blender, and the Unity bridge.

## Real Asset Autopilot

The assistant now exposes 60+ tools, including semantic asset discovery and placement tools:

- `unity_search_assets_semantic`
- `unity_find_tree_assets`, `unity_find_rock_assets`, `unity_find_prop_assets`
- `unity_find_character_assets`, `unity_find_weapon_assets`
- `unity_instantiate_best_asset`
- `unity_scatter_best_assets`
- `unity_create_forest_from_assets`
- `unity_create_rock_field_from_assets`
- `unity_get_asset_catalog_summary`

For environment and prop requests, the model is instructed to search real project assets first and use primitives only as a fallback.

## Unity Menu

```text
Window
  UnityTools AI
    Autopilot Chat

Tools
  UnityTools
    Open AI Autopilot
    Bridge Status
    Start Embedded Chat Core
    Stop Embedded Chat Core
```

## Donate

If this project helps you, donations are welcome but never required.

TRC20 wallet:

```text
TRKiVNARp8DWbU3T7ErUEz6eXRKurhNHkA
```

Thank you for trying it, sharing feedback, and helping it grow. Love and respect.

## Roadmap

- Vision scoring tool from V1
- Scene profile loader for production/gameplay/blockout profiles
- Persistent task queue on disk
- More Unity command handlers
- Richer Blender generation and validation tools
- Packaged Unity UPM distribution

## License

MIT. See `LICENSE`.
