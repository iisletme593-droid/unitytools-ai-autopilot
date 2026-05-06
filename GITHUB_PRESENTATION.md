# UnityTools AI Autopilot v2.6

UnityTools AI Autopilot is a local-first Unity Editor AI panel. It lets you chat inside Unity and gives the model real tools for scene editing, asset discovery, material repair, performance profiling, LOD/decimation planning, Blender export/import, and visual QA.

UnityTools AI Autopilot, Unity Editor icinde calisan local-first bir AI panelidir. Unity icinden sohbet edersin; model sahne duzenleme, asset bulma, material tamiri, performans profili, LOD/decimation plani, Blender export/import ve gorsel QA icin gercek tool'lar kullanir.

## Why It Exists

Many Unity AI workflows fail because they only talk. This project focuses on action:

- It reads the active scene semantically instead of trusting tags.
- It searches real project assets before falling back to primitives.
- It repairs pink/HDRP/URP material problems while preserving textures.
- It snapshots scenes before risky edits.
- It profiles heavy scenes and can add safe proxy LODs for high-poly tree/rock assets.
- It runs directly from a native Unity Editor panel.

Bir cok Unity AI akisi sadece konusur. Bu proje aksiyona odaklanir:

- Tag'lere guvenmeden sahneyi semantik okur.
- Primitive'e dusmeden once projedeki gercek assetleri arar.
- Pink/HDRP/URP material sorunlarini texture'lari koruyarak tamir eder.
- Riskli islerden once scene snapshot alir.
- Agir sahneleri profil eder ve yuksek poly tree/rock assetlerine guvenli proxy LOD ekleyebilir.
- Native Unity Editor panelinden calisir.

## v2.6 Highlights

- 90+ tools exposed to the AI
- Visual QA with SceneView screenshot capture
- Persistent asset knowledge base under `AutopilotData`
- Prefab/model quality ranking for realistic asset placement
- Scene operation planner for safe multi-step edits
- HDRP/URP/Built-in material converter
- Scene performance profiler
- LOD/Decimation Planner for very heavy scenes, including 55M+ triangle forests
- Safe proxy `LODGroup` generation for high-poly tree/rock objects
- Aggressive proxy replacement mode exists, but is snapshot-protected and should only run with explicit approval
- Snapshot and restore system
- Task queue for long jobs
- Safety modes: `safe`, `edit`, `destructive`
- Quick presets in the Unity chat panel: Snapshot, Asset DB, Fix Pink, Optimize, Visual QA, Forest Plan

## v2.6 One-Line Test Result

Live Unity validation on `Assets/Scenes/Main.unity`:

- Before: about 55.1M triangles
- Applied: 27 tree proxy LOD groups and 3 rock proxy LOD groups
- Material QA: 0 missing, 0 broken/pink, 0 unsupported materials
- Python tests: 6 passed

Canli Unity dogrulama `Assets/Scenes/Main.unity` uzerinde:

- Once: yaklasik 55.1M triangle
- Uygulanan: 27 tree proxy LOD group ve 3 rock proxy LOD group
- Material QA: 0 missing, 0 broken/pink, 0 unsupported material
- Python testleri: 6 passed

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
