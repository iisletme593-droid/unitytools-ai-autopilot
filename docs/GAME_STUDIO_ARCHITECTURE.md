# UnrealTools Game Studio Architecture

Bu proje artik sadece "assistant" degil; hedef, Unity ve Unreal icinde calisan lokal/on-prem bir dijital oyun studyosu mimarisidir.

This project is not just an assistant. The target architecture is a local/on-prem digital game studio that operates inside Unity and Unreal.

## North Star

AI sunlari parca parca degil, pipeline olarak yapabilmeli:

- Projeyi acar ve durumunu anlar
- Gameplay loop tasarlar ve uygular
- Unreal/Unity project scaffold olusturur
- Asset uretir, import eder, kataloglar ve kaliteye gore secer
- Map/level/scene uretir
- Economy, progression ve balancing tablolarini olusturur
- UI/HUD/menu/UX kurar
- Multiplayer replication kurar
- Dedicated server ayarlarini hazirlar
- Build/package alir
- Steam page capsule/key art/screenshot/trailer prompt assetlerini uretir

## Capability Levels

### Level 1 - Basic Assistant

- Chatbot
- Kod onerisi
- Aciklama ve yonlendirme

### Level 2 - Coding Agent

- Kod yazar
- Dosya duzenler
- Test calistirir

### Level 3 - Autonomous Engineering Agent

- Plan yapar
- Repo tarar
- Kod uretir
- Debug eder
- Kendini duzeltir

### Level 4 - Unreal Development Agent

- C++
- Blueprint
- Asset
- Level
- Animation
- Niagara
- Build and packaging

### Level 5 - Autonomous Game Director AI

- Combat, camera, VFX, audio, pacing ve enemy AI gibi yaratici/oynanis kararlarini verir
- Sadece teknik is yapmaz; oyunu daha eglenceli hale getirmeye calisir

### Level 6 - Self-Evolving Game Studio

- Player data okur
- Fun analysis yapar
- Harita, economy, quest, NPC davranisi ve liveops eventlerini guvenli sekilde iterasyonla degistirir
- Her denemeyi hafizaya yazar ve sonraki prototipi daha akilli baslatir

Local implementation details live in `docs/SELF_EVOLVING_GAME_STUDIO.md`.

## Agent Roles

### Studio Director

- Kullanici niyetini product/game brief'e cevirir
- Scope, risk, target platform ve milestone belirler
- Gerekirse soruyu netlestirir, sonra alt ajanlara dagitir

### Project Architect

- Unity/Unreal proje yapisini okur
- Plugin, module, package, build target, input, render pipeline ve platform kararlarini verir

### World Builder

- Map/level/terrain/lighting/fog/camera/composition kurar
- Asset katalogundan real asset secer
- Primitive'i sadece fallback olarak kullanir

### Gameplay Engineer

- Core loop, controller, interaction, combat, inventory, quest, economy ve save sistemlerini uygular
- Unity C# veya Unreal Blueprint/C++/Python editor scripting arasinda uygun yolu secer

### Asset Director

- Asset arar, import eder, tagler, isimlendirir, kalite/LOD/performance skorlar
- Bozuk material, pink shader, invalid texture, duplicate import ve heavy mesh risklerini tamir eder

### Multiplayer Engineer

- Unreal replication, GameMode/GameState/PlayerState, RPC, dedicated server hedefleri
- Unity Netcode/Mirror/FishNet gibi secilebilir backend stratejileri

### Build & Release Engineer

- Build target, packaging, dedicated server, CI, versioning
- Steam page assetleri, store checklist, screenshots ve metadata

### QA / Profiler

- Scene/map snapshot alir
- Visual QA, performance profile, triangle/poly budget, memory ve import error raporu uretir
- Riskli islemlerde rollback noktasi olusturur

## Tool Pillars

### Project Control

- project_open
- project_status
- project_create
- package_install
- build_target_configure

### Asset Pipeline

- asset_catalog_build
- asset_search_semantic
- asset_import_batch
- asset_convert_blender
- asset_repair_materials
- asset_generate_proxy_lod
- asset_score_quality

### World / Level

- level_list/open/save
- level_create
- actor/list/search/spawn/delete/transform
- terrain/landscape_create
- foliage_scatter
- lighting_fog_camera_setup

### Gameplay

- create_gameplay_loop
- create_character_controller
- create_interaction_system
- create_inventory
- create_combat
- create_economy_table
- create_save_system

### UI

- create_main_menu
- create_hud
- create_inventory_ui
- create_settings_ui
- localize_ui

### Multiplayer

- enable_replication
- create_replicated_actor
- create_rpc
- configure_dedicated_server
- test_listen_server

### Build / Release

- build_client
- build_dedicated_server
- run_smoke_test
- generate_steam_capsule_prompts
- generate_store_copy
- export_screenshots

## Execution Contract

1. Once oku: proje, level, asset katalogu, build hedefi.
2. Sonra planla: milestone ve riskleri yaz.
3. Sonra uygula: tool call kullan, JSON basip birakma.
4. Her riskli isten once snapshot/backup al.
5. Uzun islerde manifest/resume kullan.
6. Sonunda QA: compile/build/ping/profile/screenshot kontrolu.

## Unreal First Milestones

### v2.8

- Unreal panel auto-open + visible top menu
- Unreal project scanner
- Unreal asset catalog cache
- Actor semantic edit pack
- Batch import resume UI

Implemented first-pass studio operators:

- `unreal_scan_project`
- `unreal_create_basic_level`
- `unreal_setup_studio_lighting`
- `unreal_create_blockout_map`

These tools make the default loop: scan -> plan -> create level/blockout -> light/camera -> save.

### v2.9

- Level generator: blockout, terrain, lighting, camera
- Foliage/rock/prop scatter with performance budgets
- Material repair and texture validation

### v3.0

- Gameplay loop generator
- UI/HUD/menu generator
- Economy table generator
- Save system scaffold

### v3.1

- Multiplayer replication planner
- Dedicated server target setup
- Smoke test runner

### v3.2

- Steam page asset/copy generator
- Build/release checklist
- Visual QA dashboard

## Notlar

Epic'in kendi `AIAssistant` pluginini bozmak yerine bizim `UnrealToolsBridge` pluginimiz bu oyun studyosu mimarisinin merkezi olacak. Bu daha guvenli, surdurulebilir ve GitHub'da paylasilabilir bir yol.
