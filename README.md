# UnityTools AI Autopilot

UnityTools AI Autopilot is a local-first AI panel for Unity and Unreal Editor. It lets you chat inside the editor and lets the model call real Unity, Unreal, and Blender tools: create scene objects/actors, search and place real project assets, list the active scene/level, import assets, export FBX files from Blender, and run pipeline steps.

UnityTools AI Autopilot, Unity ve Unreal Editor icinde calisan local-first bir AI panelidir. Editor icinden sohbet edersin; model gercek Unity, Unreal ve Blender tool'larini cagirarak sahne objeleri/actor'lar olusturur, projedeki gercek assetleri arar ve yerlestirir, aktif sahne/level'i listeler, asset import eder, Blender'dan FBX export eder ve pipeline adimlarini calistirir.

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
- v2.5 Autopilot Quality Layer: visual QA screenshots, asset knowledge base, prefab quality ranking, safety modes, scene snapshots, task queue, and scene performance profiler
- v2.5 Autopilot Kalite Katmani: gorsel QA screenshot, asset bilgi tabani, prefab kalite siralama, safety mode, scene snapshot, task queue ve performans profiler
- v2.6 LOD/Decimation Planner: finds high-poly mesh groups and adds safe proxy LODs for heavy tree/rock scenes
- v2.6 LOD/Decimation Plani: yuksek poly mesh gruplarini bulur ve agir tree/rock sahneleri icin guvenli proxy LOD ekler
- Batch placement tools for forests, rock fields, prop clusters, asset grids, lines, and rings
- Orman, kaya alani, prop kumesi, asset grid/line/ring icin batch yerlestirme tool'lari
- Blender headless bridge for `.blend` to `.fbx` export workflows
- `.blend` -> `.fbx` export icin headless Blender bridge
- Undo-aware Unity commands for created objects and transform changes
- Olusturulan objeler ve transform degisiklikleri icin Undo destekli Unity komutlari
- GitHub-ready MIT licensed project
- GitHub'a hazir MIT lisansli proje
- v2.7 Unreal Engine bridge and embedded Unreal Editor chat tab
- v2.7 Unreal Engine bridge ve Unreal Editor icinde gomulu chat sekmesi

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

**Default: Hierarchical Dual-Agent Mode / Varsayilan: Hiyerarsik Dual-Agent**

The embedded Unity panel now starts a three-role local hierarchy by default:

Unity icindeki panel artik varsayilan olarak uc rollu lokal hiyerarsi baslatir:

- Reader: fast scene/asset/context scan, default `qwen2.5:14b-instruct`
- Master: deeper planning, default `qwen3.6:latest` with automatic fallback if missing
- Worker: tool execution / Unity changes, default `qwen2.5:14b-instruct`

- Reader: hizli sahne/asset/context okuma, varsayilan `qwen2.5:14b-instruct`
- Master: daha derin planlama, varsayilan `qwen3.6:latest`; kurulu degilse otomatik fallback
- Worker: tool execution / Unity degisiklikleri, varsayilan `qwen2.5:14b-instruct`

```powershell
ollama pull qwen2.5:14b-instruct
ollama pull qwen3.6:latest

# Optional terminal mode
unitytools dual-chat --reader qwen2.5:14b-instruct --master qwen3.6:latest --worker qwen2.5:14b-instruct
```

In the embedded Unity panel, dual-agent is enabled by default. You can override roles through `.env`:

Unity icindeki gomulu panelde dual-agent varsayilan aciktir. Rolleri `.env` ile degistirebilirsin:

```env
USE_DUAL_AGENT=true
DUAL_AGENT_READER=qwen2.5:14b-instruct
DUAL_AGENT_MASTER=qwen3.6:latest
DUAL_AGENT_WORKER=qwen2.5:14b-instruct
```

If `qwen3.6:latest` is not installed, the CLI falls back to the configured `OLLAMA_MODEL`.

`qwen3.6:latest` kurulu degilse CLI otomatik olarak `OLLAMA_MODEL` degerine duser.

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

This installs Unity-side files safely / Bu komut Unity tarafindaki dosyalari guvenli kurar:

- `Assets/Editor/UnityToolsBridge`: embedded chat panel and TCP bridge / gomulu chat paneli ve TCP bridge
- `Assets/Scripts/Autopilot`: Autopilot task, scene, HDRP, asset, and vision scripts / Autopilot task, sahne, HDRP, asset ve vision scriptleri
- `Assets/Editor/UnityToolsAutopilot`: Autopilot import and maintenance helpers, only when matching root-level helpers do not already exist / Autopilot import ve bakim yardimcilari, sadece ayni helper'lar root `Assets/Editor` altinda yoksa

Autopilot runs in manual/chat-controlled mode by default. It will not run scene builders, migrations, material swaps, or brain loops automatically on Unity reload. Use chat commands or explicit menu items when you want it to act.

Autopilot varsayilan olarak manuel/chat kontrollu modda calisir. Unity reload sonrasi kendi kendine scene builder, migration, material swap veya brain loop calistirmaz. Bir islem istediginde chat komutu ya da acik menu komutu kullan.

6. Open Unity and launch / Unity'yi ac ve paneli baslat:

```text
Window > UnityTools AI > Autopilot Chat
```

The panel starts the Python chat core in the background. No external terminal window is required.

Panel Python chat core'u arka planda baslatir. Harici terminal penceresi gerekmez.

The panel also includes quick presets: `Snapshot`, `Asset DB`, `Fix Pink`, `Optimize`, `Visual QA`, and `Forest Plan`.

Panelde hizli presetler de vardir: `Snapshot`, `Asset DB`, `Fix Pink`, `Optimize`, `Visual QA` ve `Forest Plan`.

The panel includes a Turkish scene selector. Pick the scene you want to work on, click `Sahneyi Ac`, then chat commands operate on that active scene.

Panelde Turkce sahne secici vardir. Calismak istedigin sahneyi sec, `Sahneyi Ac` butonuna bas; sonraki chat komutlari aktif olan o sahnede calisir.

## Optional: Anthropic Mode

If you prefer Claude, set / Claude kullanmak istersen:

```env
UNITYTOOLS_PROVIDER=anthropic
ANTHROPIC_API_KEY=<your-anthropic-api-key>
UNITYTOOLS_MODEL=claude-sonnet-4-20250514
```

## Unreal Engine Quick Start

Unreal Engine destegi v2.7 ile gelir. Native sekme:

```text
Unreal acilinca panel otomatik acilir.
Top menu: UnrealTools AI > Open UnrealTools AI Chat
Tools > UnrealTools > Open UnrealTools AI Chat
Window > UnrealTools > Open UnrealTools AI Chat
```

Install the plugin / Plugin'i kur:

```powershell
unitytools install-unreal-plugin --project "C:\Path\To\UnrealProject\Project.uproject"
```

Open/restart Unreal, then test / Unreal'i ac veya yeniden baslat, sonra test et:

```powershell
unitytools unreal-ping
```

The Unreal plugin exposes:

- `unreal_list_level_actors`
- `unreal_find_level_actors_semantic`
- `unreal_search_assets_semantic`
- `unreal_get_asset_catalog_summary`
- `unreal_spawn_basic_actor`
- `unreal_delete_actors_semantic`
- `unreal_set_actor_transform`
- `unreal_import_asset`
- `unreal_stage_unity_assets_for_migration`

Unity asset migration / Unity assetlerini Unreal'a tasima:

```powershell
unitytools migrate-unity-assets-to-unreal `
  --unity-project "C:\Path\To\UnityProject" `
  --staging "D:\UnityToolsV2\UnrealMigrationStaging" `
  --import-into-unreal `
  --category-folders `
  --replace-existing `
  --import-mode safe_static `
  --batch-size 25
```

Long imports are resumable through `UnrealMigrationStaging/unreal_import_manifest.json`.

Uzun importlar `UnrealMigrationStaging/unreal_import_manifest.json` ile kaldigi yerden devam eder.

More detail / Detay: [Unreal Engine Support](docs/UNREAL.md)

Long-term target / Uzun vadeli hedef: [Game Studio Architecture](docs/GAME_STUDIO_ARCHITECTURE.md)

The Unreal panel is now styled as a premium local game-studio cockpit with auto-open, safe auto-connect, message cards, status chips, and studio presets for project scan, level planning, gameplay loop, UI/HUD, multiplayer, and build/release work.

Unreal paneli artik premium lokal oyun studyosu kokpiti gibi calisir: auto-open, guvenli auto-connect, mesaj kartlari, status chipleri ve project scan, level planning, gameplay loop, UI/HUD, multiplayer, build/release presetleri vardir.

First studio operator tools are live: `unreal_scan_project`, `unreal_create_basic_level`, `unreal_setup_studio_lighting`, and `unreal_create_blockout_map`.

Ilk studio operator araclari aktif: `unreal_scan_project`, `unreal_create_basic_level`, `unreal_setup_studio_lighting` ve `unreal_create_blockout_map`.

## Dual-Agent System

UnityTools supports an advanced hierarchical dual-agent system with learning capabilities:

- 📘 **[Quick Start Guide](DUAL_AGENT_QUICKSTART.md)** - 5 dakikada başlangıç
- 📗 **[Complete Guide](DUAL_AGENT_GUIDE.md)** - Detaylı kullanım kılavuzu
- 📙 **[Philosophy](DUAL_AGENT_PHILOSOPHY.md)** - Neden iyi planlama önemli?
- 📕 **[Technical Summary](DUAL_AGENT_SUMMARY.md)** - API ve mimari detayları
- 🚀 **[Enhanced Features](ENHANCED_FEATURES.md)** - Memory & Context (NEW!)
- ✅ **[Integration Report](FINAL_INTEGRATION_REPORT.md)** - Full test results

**TL;DR**: 
- Reader/Worker default to Qwen 2.5:14b-instruct for fast scene reading and tool execution
- Master defaults to Qwen 3.6 for deeper planning, with fallback if missing
- The Unity panel starts dual-agent mode by default
- JSON tool-call rescue converts printed tool JSON into real Unity tool calls
- **Memory system** learns from every task
- **Context manager** tracks scene state
- Gets **22% faster** on repeated tasks
- **95% success rate** (vs 70% basic)

## Diagnostics

```powershell
unitytools doctor
unitytools status
unitytools unity-ping
unitytools cleanup-processes
```

`doctor` checks Ollama, the selected model, Blender, and the Unity bridge.

`doctor`, Ollama'yi, secili modeli, Blender'i ve Unity bridge baglantisini kontrol eder.

`cleanup-processes` stops stale embedded chat-server processes if Unity was closed while background tools were alive.

`cleanup-processes`, Unity kapanirken arkada kalmis gomulu chat-server sureclerini kapatir.

## Real Asset Autopilot

The assistant now exposes 90+ tools, including semantic asset discovery, scene intelligence, visual QA, safety snapshots, asset memory, palette, performance, and placement tools.

Asistan artik 90+ tool sunar; buna semantic asset kesfi, scene intelligence, gorsel QA, guvenli snapshot, asset hafizasi, renk paleti, performans ve yerlestirme tool'lari dahildir:

- `unity_search_assets_semantic`
- `unity_find_tree_assets`, `unity_find_rock_assets`, `unity_find_prop_assets`
- `unity_find_character_assets`, `unity_find_weapon_assets`
- `unity_instantiate_best_asset`
- `unity_scatter_best_assets`
- `unity_create_forest_from_assets`
- `unity_create_rock_field_from_assets`
- `unity_get_asset_catalog_summary`
- `unity_get_scene_catalog`
- `unity_find_scene_objects_semantic`
- `unity_delete_scene_objects_semantic`
- `unity_apply_material_palette`
- `unity_diagnose_material_issues`
- `unity_repair_material_issues`
- `unity_repair_texture_import_settings`
- `unity_create_optimized_forest_scene`
- `unity_optimize_editor_performance`
- `unity_export_scene_knowledge_base`
- `unity_run_visual_qa`
- `unity_profile_scene_performance`
- `unity_analyze_lod_decimation_candidates`
- `unity_create_lod_decimation_plan`
- `unity_apply_lod_decimation_plan`
- `unity_list_scenes`, `unity_open_scene`
- `unity_create_scene_snapshot`, `unity_restore_scene_snapshot`
- `unity_build_asset_knowledge_base`
- `unity_rank_prefab_quality`
- `unity_plan_scene_operation`
- `unity_auto_convert_materials_to_pipeline`
- `unity_set_autopilot_safety_mode`, `unity_get_autopilot_safety_mode`
- `unity_create_task_queue`, `unity_get_task_queue`, `unity_update_task_status`

For environment and prop requests, the model is instructed to search real project assets first and use primitives only as a fallback.

For risky edits, the model is instructed to snapshot first, then validate with visual QA and performance profiling.

Riskli duzenlemelerde model once snapshot alacak, sonra visual QA ve performans profili ile sonucu dogrulayacak sekilde yonlendirilir.

## Support / Donate

If this project helps you, stars, issues, pull requests, and donations are welcome. Donations are optional and never required.

Bu proje isine yararsa star, issue, pull request ve bagislar memnuniyetle karsilanir. Bagis tamamen opsiyoneldir, zorunlu degildir.

TRC20 donation wallet / TRC20 bagis cuzdanı:

```text
TRKiVNARp8DWbU3T7ErUEz6eXRKurhNHkA
```

Environment ve prop isteklerinde model once projedeki gercek assetleri arar; primitive/kup gibi objeleri sadece fallback olarak kullanir.

For scene edits, the model is instructed not to rely on Unity tags. It reads names, hierarchy paths, materials, components, and semantic categories instead, so `tree`, `agac`, `rock`, `campfire`, `ground`, and similar phrases work even when every object is `Untagged`.

Sahne duzenlemelerinde model artik Unity tag'lerine guvenmez. Isim, hierarchy path, material, component ve semantic kategori okur; bu yuzden tum objeler `Untagged` olsa bile `tree`, `agac`, `rock`, `campfire`, `ground` gibi komutlar calisir.

More detail / Daha fazla detay: [Scene Intelligence](docs/SCENE_INTELLIGENCE.md)

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
