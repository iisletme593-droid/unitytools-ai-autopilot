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

> See `GAME_STUDIO_ROADMAP.md` for the backlog and `GAME_STUDIO_PROGRESS.md` for the per-cycle log.
