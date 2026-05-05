# UnityTools AI Autopilot

UnityTools AI Autopilot is a local-first AI panel for the Unity Editor. It lets you chat inside Unity and lets the model call real Unity and Blender tools: create scene objects, search and place real project assets, list the active scene, import assets, export FBX files from Blender, and run pipeline steps.

UnityTools AI Autopilot, Unity Editor icinde calisan local-first bir AI panelidir. Unity icinden sohbet edersin; model gercek Unity ve Blender tool'larini cagirarak sahne objeleri olusturur, projedeki gercek assetleri arar ve yerlestirir, aktif sahneyi listeler, asset import eder, Blender'dan FBX export eder ve pipeline adimlarini calistirir.

The default setup uses Ollama with `qwen2.5:14b-instruct`, so it can run without a paid API key. Anthropic Claude is still supported for users who want a stronger cloud model.

Varsayilan kurulum Ollama ile `qwen2.5:14b-instruct` kullanir; bu yuzden ucretli API key gerekmeden lokal calisir. Daha guclu cloud model isteyenler icin Anthropic Claude destegi de duruyor.

## Highlights

- Native Unity Editor panel: `Window > UnityTools AI > Autopilot Chat`
- Unity Editor icinde gomulu panel: `Window > UnityTools AI > Autopilot Chat`
- No terminal needed during normal use: the panel starts the Python chat core silently
- Normal kullanimda terminal gerekmez: panel Python chat core'u arka planda sessiz baslatir
- Local/free model path with Ollama and `qwen2.5:14b-instruct`
- Ollama + `qwen2.5:14b-instruct` ile lokal/ucretsiz model akisi
- Optional Anthropic provider for higher quality reasoning
- Daha yuksek muhakeme kalitesi icin opsiyonel Anthropic provider
- Tool calling into Unity Editor over localhost TCP
- Localhost TCP uzerinden Unity Editor'e tool call
- Semantic Unity asset catalogue: finds real assets even from fuzzy prompts like `real relis realist tree`
- Semantic Unity asset katalogu: `real relis realist tree` gibi bozuk/fuzzy promptlarda bile gercek asset bulur
- Batch placement tools for forests, rock fields, prop clusters, asset grids, lines, and rings
- Orman, kaya alani, prop kumesi, asset grid/line/ring icin batch yerlestirme tool'lari
- Blender headless bridge for `.blend` to `.fbx` export workflows
- `.blend` -> `.fbx` export icin headless Blender bridge
- Undo-aware Unity commands for created objects and transform changes
- Olusturulan objeler ve transform degisiklikleri icin Undo destekli Unity komutlari
- GitHub-ready MIT licensed project
- GitHub'a hazir MIT lisansli proje

## What It Can Do

Try prompts like / Su promptlari dene:

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

1. Install Ollama / Ollama kur:

```powershell
winget install --id Ollama.Ollama -e
```

2. Pull the recommended local model / Onerilen lokal modeli indir:

```powershell
ollama pull qwen2.5:14b-instruct
```

3. Install the Python package from this repository / Python paketini bu repodan kur:

```powershell
pip install -e .
copy .env.example .env
```

4. Make sure `.env` uses Ollama / `.env` dosyasinin Ollama kullandigindan emin ol:

```env
UNITYTOOLS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:14b-instruct
```

5. Install the Unity Editor bridge into your Unity project / Unity Editor bridge'i Unity projesine kur:

```powershell
unitytools install-unity-plugin --project "C:\Path\To\YourUnityProject"
```

6. Open Unity and launch / Unity'yi ac ve paneli baslat:

```text
Window > UnityTools AI > Autopilot Chat
```

The panel starts the Python chat core in the background. No external terminal window is required.

Panel Python chat core'u arka planda baslatir. Harici terminal penceresi gerekmez.

## Optional: Anthropic Mode

If you prefer Claude, set / Claude kullanmak istersen:

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

`doctor`, Ollama'yi, secili modeli, Blender'i ve Unity bridge baglantisini kontrol eder.

## Real Asset Autopilot

The assistant now exposes 60+ tools, including semantic asset discovery and placement tools.

Asistan artik 60+ tool sunar; buna semantic asset kesfi ve yerlestirme tool'lari dahildir:

- `unity_search_assets_semantic`
- `unity_find_tree_assets`, `unity_find_rock_assets`, `unity_find_prop_assets`
- `unity_find_character_assets`, `unity_find_weapon_assets`
- `unity_instantiate_best_asset`
- `unity_scatter_best_assets`
- `unity_create_forest_from_assets`
- `unity_create_rock_field_from_assets`
- `unity_get_asset_catalog_summary`

For environment and prop requests, the model is instructed to search real project assets first and use primitives only as a fallback.

Environment ve prop isteklerinde model once projedeki gercek assetleri arar; primitive/kup gibi objeleri sadece fallback olarak kullanir.

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

Bu proje isine yararsa bagis kabul edilir ama asla zorunlu degildir.

TRC20 wallet:

```text
TRKiVNARp8DWbU3T7ErUEz6eXRKurhNHkA
```

Thank you for trying it, sharing feedback, and helping it grow. Love and respect.

Deneyen, geri bildirim veren ve gelismesine destek olan herkese tesekkurler. Sevgi ve saygilar.

## Roadmap

- Vision scoring tool from V1
- Scene profile loader for production/gameplay/blockout profiles
- Persistent task queue on disk
- More Unity command handlers
- Richer Blender generation and validation tools
- Packaged Unity UPM distribution

## License

MIT. See `LICENSE`.

