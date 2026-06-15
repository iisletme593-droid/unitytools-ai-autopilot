# Game-Studio Tools (autopilot capabilities)

Tools added during the autonomous overnight work (branch `autonomous/game-studio`). The autopilot
calls these via the Unity bridge; you drive them with natural-language commands in the chat panel.
All pure math behind them is unit-tested (`pytest tests/`).

## Placement & level blockout
| Tool | What it does | Example command |
|------|--------------|-----------------|
| `unity_place_primitives` | Place N primitives in a layout (grid/circle/line/scatter) | "20 küpü çember düzeninde yerleştir" |
| `unity_build_structure` | Block out a structure from primitives | "5x3 bir duvar ör", "build a 4-high tower", "bir merdiven yap" |
| `unity_blockout_scene` | One-shot: floor + scattered props + studio lighting + framed camera | "boş sahneden kompoze bir sahne kur" |

Patterns: `grid`, `circle`, `line`, `scatter` · Structures: `wall`, `tower`, `stairs`, `room`, `floor`.
Safety caps prevent flooding the scene (≤500 objects per call, 17×17 floor).

## Lighting & camera (presentable scenes)
| Tool | What it does | Example command |
|------|--------------|-----------------|
| `unity_setup_studio_lighting` | 3-point key/fill/rim rig around a target | "sahneye stüdyo ışığı kur" |
| `unity_frame_camera` | Orbit/frame the camera on a target (distance/yaw/pitch, optional fov) | "kamerayı sahneyi gösterecek şekilde çerçevele" |

## Color & materials
| Tool | What it does | Example command |
|------|--------------|-----------------|
| `unity_set_object_color` | Set a color by name (en/tr), hex, or r,g,b | "Cube'u kırmızı yap", "make Player gold" |
| `unity_color_group` | Color a named group with a theme palette, cycling | "Prop grubunu fantasy temasında renklendir" |

Color names work in English and Turkish (red/kırmızı, blue/mavi, gold/altın…). Themes: `fantasy`,
`nature`, `warm`, `cool`, `mono`.

## Reliability improvements
- **Repeated-tool-call guard:** the autopilot no longer spins creating the same object over and over
  (fixes the "10 spheres for one request" bug); it stops after the action is done.
- **Honest results:** `unity_save_scene` reports a real failure instead of always claiming success.

## Wired bridge power (day 1) — capabilities that existed in the C# bridge but had no tool
These were already implemented in the bridge; they now have `unity_*` wrappers so the autopilot can
actually call them. Params are grounded in the real C# handlers.

| Tool | What it does | Example command |
|------|--------------|-----------------|
| `unity_apply_material_palette` | Re-skin scene materials with a themed palette, preserving textures | "Sahnedeki materyallere orman paletini uygula" |
| `unity_diagnose_material_issues` | Report missing/broken/unsupported materials (read-only) | "Sahnedeki bozuk materyalleri tara" |
| `unity_repair_material_issues` | Recreate broken materials, optionally tint with a palette | "Bozuk materyalleri onar" |
| `unity_repair_texture_import_settings` | Normalize texture import (mipmaps, sRGB/linear, compression) | "Doku import ayarlarını düzelt" |
| `unity_create_optimized_forest_scene` | Generate a perf-optimized forest (terrain+trees+rocks+fog+light+cam) from a seed | "150 ağaçlı optimize orman sahnesi kur" |
| `unity_get_scene_catalog` | Full catalog of the scene: per-object category/tag/pos/components + group counts | "Sahnenin kataloğunu çıkar" |
| `unity_find_scene_objects_semantic` | Find objects by semantic query/category | "Sahnedeki tüm ağaçları bul" |
| `unity_delete_scene_objects_semantic` | Delete objects by semantic query/category | "Sahnedeki tüm kayaları sil" |
| `unity_run_visual_qa` | QA pass: counts + material flags + verdict, optional screenshot | "Sahnede görsel kalite kontrolü yap" |
| `unity_create_scene_snapshot` / `unity_restore_scene_snapshot` | Save/restore a timestamped scene snapshot (safe experimentation) | "Sahnenin anlık görüntüsünü al" |
| `unity_profile_scene_performance` | Vertex/triangle/draw cost profile + optimization suggestions | "Sahne performansını analiz et" |
| `unity_optimize_editor_performance` | Speed up the editor for heavy scenes (shadows/LOD/vSync) | "Editörü bu ağır sahne için optimize et" |
| `unity_analyze_lod_decimation_candidates` / `unity_apply_lod_decimation_plan` | Find heavy meshes & add LOD groups with proxies | "Ağır ağaçlara LOD ekle" |

## Quality loop & safety (day 1)
- **`unity_quality_pass`** — runs the build→QA→fix loop: visual-QA the scene, then auto-repair
  broken/missing materials and add lighting if missing, then re-check. Snapshots before fixing.
  "Sahnenin kalitesini kontrol et ve sorunları düzelt."
- **Auto-snapshot safety** — before the first *destructive* tool of a turn (delete, wipe-and-
  regenerate, material/LOD rewrite), the orchestrator auto-saves a scene snapshot so the user can
  roll back with `unity_restore_scene_snapshot`. One snapshot per turn, best-effort.

## Gameplay authoring

Beyond decorating scenes, the autopilot can author **gameplay**: physics behaviours
(`unity_add_gameplay_behaviour`), scripted MonoBehaviours (`unity_add_script_behaviour` /
`unity_apply_script_behaviour` — rotate/move/player/collectible/goal/killzone/spawner), and whole
playable games (`unity_build_simple_game` — collectathon / dodge / survival). Natural-language
"build me a game" requests route there automatically.

→ Full reference (game types, behaviour catalog, example commands, recompile notes):
**`GAME_STUDIO_GAMES.md`**.

> See `GAME_STUDIO_ROADMAP.md` for the backlog and `GAME_STUDIO_PROGRESS.md` for the per-cycle log.
