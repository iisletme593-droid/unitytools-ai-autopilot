# UnityTools AI Autopilot v2.5

UnityTools AI Autopilot is a local-first Unity Editor AI panel. It lets you chat inside Unity and gives the model real tools for scene editing, asset discovery, material repair, performance profiling, Blender export/import, and visual QA.

UnityTools AI Autopilot, Unity Editor icinde calisan local-first bir AI panelidir. Unity icinden sohbet edersin; model sahne duzenleme, asset bulma, material tamiri, performans profili, Blender export/import ve gorsel QA icin gercek tool'lar kullanir.

## Why It Exists

Many Unity AI workflows fail because they only talk. This project focuses on action:

- It reads the active scene semantically instead of trusting tags.
- It searches real project assets before falling back to primitives.
- It repairs pink/HDRP/URP material problems while preserving textures.
- It snapshots scenes before risky edits.
- It profiles heavy scenes and suggests optimization.
- It runs directly from a native Unity Editor panel.

Bir cok Unity AI akisi sadece konusur. Bu proje aksiyona odaklanir:

- Tag'lere guvenmeden sahneyi semantik okur.
- Primitive'e dusmeden once projedeki gercek assetleri arar.
- Pink/HDRP/URP material sorunlarini texture'lari koruyarak tamir eder.
- Riskli islerden once scene snapshot alir.
- Agir sahneleri profil eder ve optimize eder.
- Native Unity Editor panelinden calisir.

## v2.5 Highlights

- 90+ tools exposed to the AI
- Visual QA with SceneView screenshot capture
- Persistent asset knowledge base under `AutopilotData`
- Prefab/model quality ranking for realistic asset placement
- Scene operation planner for safe multi-step edits
- HDRP/URP/Built-in material converter
- Scene performance profiler
- Snapshot and restore system
- Task queue for long jobs
- Safety modes: `safe`, `edit`, `destructive`
- Quick presets in the Unity chat panel: Snapshot, Asset DB, Fix Pink, Optimize, Visual QA, Forest Plan

## Local Model

Default local model:

```env
UNITYTOOLS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:14b-instruct
```

Install:

```powershell
ollama pull qwen2.5:14b-instruct
pip install -e .
unitytools install-unity-plugin --project "C:\Path\To\UnityProject"
```

Open Unity:

```text
Window > UnityTools AI > Autopilot Chat
```

## Donation

If the project helps you, donations are welcome but never required.

Proje isine yararsa bagis yapabilirsin, ama tamamen opsiyoneldir.

TRC20:

```text
TRKiVNARp8DWbU3T7ErUEz6eXRKurhNHkA
```
