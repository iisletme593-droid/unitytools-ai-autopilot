# Autonomous Game-Studio Roadmap

**North star (aspirational):** an autopilot that can build a high-quality game from scratch —
creative scene/level design, materials/lighting, gameplay systems, asset pipeline, iteration &
learning. AAA is the *direction*, not an overnight deliverable. Each night = concrete, verified,
incremental capability gains.

**Working rules (every cycle):**
1. Work ONLY on branch `autonomous/game-studio`. Never touch `main`, never delete data, never
   commit secrets (`.env`, `*.pem`).
2. Pick the highest-priority unchecked item below (or a clear sub-step of it).
3. Implement a small, focused change. Keep cycles bounded.
4. **Verify:** `pytest` must pass and `python -c "import unitytools..."` must succeed. If a change
   breaks them and can't be fixed quickly, revert it.
5. Commit with a clear message, append a line to `docs/GAME_STUDIO_PROGRESS.md`, push the branch.
6. Schedule the next cycle.

## Backlog (priority order)

### P0 — Autopilot reliability (fix what we just saw)
- [x] **Stop over-creation / max-iterations.** (cycle 1) Added a repeated-tool-call guard in the
  ollama/cloudflare tool loops: if the model requests the same tool-call set twice in a row, stop
  with `stop_reason=repeated_tool_calls`. Verified: identical calls run once then stop; distinct
  calls still work. Follow-ups (b) prompt rule + (c) honor explicit counts remain.
- [ ] **Single vs batch intent.** Parse "bir/tek/one" vs "N tane/birçok/many" → set creation count;
  default to 1 when unspecified.
- [ ] **Completion detection.** After a successful mutating tool, prefer ending the turn unless the
  user asked for more.

### P1 — Level / scene building (toward "placement")
- [ ] High-level layout tools: place N objects in grid / circle / scatter with spacing & jitter.
- [ ] Structure composition: build simple structures (wall, room, tower) from primitives.
- [ ] Camera/lighting presets for a presentable scene.

### P2 — Visual quality (toward "AAA look", pipeline-agnostic where possible)
- [ ] Material setup tools (PBR-ish: base color, metallic, smoothness) via the bridge.
- [ ] Lighting rigs (key/fill/rim, ambient, fog) presets.
- [ ] Post-process / quality-tier helpers (guarded so they no-op without URP/HDRP).

### P3 — Learning & memory (toward "learning / focus")
- [ ] Make long-term memory actually READ BACK (cross-session learning is currently write-only).
- [ ] Feed recalled patterns/lessons into planning prompts.
- [ ] Game-studio kernel: tighten the evolution loop (metrics → weak points → next plan).

### P4 — Robustness (from the original audit)
- [ ] RPC request/response correlation after timeouts.
- [ ] Anthropic loop 400-lock on unanswered tool_use blocks.
- [ ] Stop "ok=true" lies (save_scene, blender export, unreal import).
- [ ] Fix dual_agent mojibake (UTF-8 prompts).

### P5 — Tests & docs
- [ ] Unit tests for new tools + the P0 loop logic.
- [ ] Keep docs in sync.

> Check items off in this file as they land. Add new items as discovered.
