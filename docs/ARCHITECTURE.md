# Architecture

UnityTools AI has three local runtime layers.

```text
Unity Editor panel
  -> Python chat core
  -> model provider: Ollama or Anthropic
  -> tool registry
  -> Unity bridge and Blender bridge
```

## Processes

1. Unity Editor
   - Hosts the native IMGUI panel.
   - Starts the Python chat core silently when the panel opens.
   - Runs `BridgeServer.cs` on port `7777` for scene commands.

2. Python chat core
   - Runs `unitytools chat-server` on port `7778`.
   - Owns chat history and provider-specific tool calling.
   - Supports `ollama` and `anthropic` providers.

3. Blender subprocess
   - Runs headless only when a Blender tool is called.
   - Uses scripts under `scripts/blender/`.

## Ports

- `7777`: Python -> Unity command bridge.
- `7778`: Unity panel -> Python chat core.
- `11434`: Ollama local API, when using the Ollama provider.

All traffic is local to `127.0.0.1`.

## Tool Calling

Tools are registered with the `@tool` decorator. The registry can export schemas in Anthropic format or OpenAI/Ollama function-tool format.

Current tool groups:

- Unity tools: ping, list scene objects, create primitive, import asset, save scene, set position.
- Blender tools: list objects, export FBX.
- Pipeline tools: export from Blender and import into Unity.

## Unity Threading

Unity Editor API calls must run on the main thread. The bridge accepts TCP requests on background threads, queues them, and dispatches them from `EditorApplication.update`.

## Provider Strategy

Ollama is the default because it is local and free. Anthropic remains available for stronger reasoning.

```env
UNITYTOOLS_PROVIDER=ollama
OLLAMA_MODEL=qwen3:4b
```

or:

```env
UNITYTOOLS_PROVIDER=anthropic
ANTHROPIC_API_KEY=<your key>
UNITYTOOLS_MODEL=claude-sonnet-4-20250514
```
