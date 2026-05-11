# Agent Game Developer Studio

Studio: kendi kendine plan yapan, tasarlayan, eleştiren ve uygulayan
otonom oyun gelistirici sistem. Studio: a self-planning,
self-designing, self-critiquing, self-executing autonomous game
development agent stack on top of UnityTools.

## What it is

Studio takes a Unity (or Unreal) project and runs an LLM-driven team
across it. The team writes the GDD, blocks out levels by comparing
screenshots against reference images, runs daily standups, dispatches
tasks to workers that actually edit the scene, and journals every
decision to disk so the next session starts where the last one
ended. Every step is local-first: works against Anthropic Claude, or
fully offline against Ollama (Gemma 4, Qwen 2.5, Llama 3.x).

```text
       reviews/<date>.md  <-  Producer plans + retros
                              |
                              v
       backlog.json   <- Producer / Critic open tasks
            |
            v
       Dispatcher  ->  Designer / Critic / Art Director  (text work)
            |
            ' ----- > Worker  (Unity scene edits, snapshot + verify)
                              |
                              v
       qa/regression.jsonl  <- visual diff scores per pass
       qa/screenshots/      <- captured frames
       decisions.jsonl      <- append-only design rationale
```

## Quick start

5-minute walkthrough. Lokal Ollama + Gemma 4 ile hicbir API key
gerekmez.

```sh
# 1. Install
pip install -e .

# 2. Pick a project root (Unity project or any directory)
mkdir my-game && cd my-game

# 3. Scaffold the studio layout
unitytools studio-init --project .

# 4. Edit studio/gdd.md and write a one-line pitch (or skip; the
#    Designer will draft a placeholder).

# 5. Set provider (one-time, in .env or shell env)
export UNITYTOOLS_PROVIDER=ollama
export OLLAMA_MODEL=gemma4:latest

# 6. First contact: dry-run, no API calls, reads + writes disk
unitytools studio-run --role designer --dry-run

# 7. Real run: Gemma 4 writes a real GDD pitch
unitytools studio-run --role designer

# 8. Plan a day's work
unitytools studio-review --phase morning

# 9. Auto-execute the backlog
unitytools studio-autopilot --max-tasks 5
```

## Architecture

Studio is built in layers. Each phase below maps to a single import-
graph layer; later phases depend only on earlier ones, never sideways.

| Phase | Layer | What it adds |
|---|---|---|
| 1 | `studio/state.py`, `models.py`, `paths.py` | Atomic JSON / append-only JSONL on disk |
| 2 | `studio/tools.py`, `roles.py`, `runner.py` | 14 doc tools, 3 doc-only roles, RoleRunner with sandbox + protocol-based LLM client |
| 3 | `studio/vision.py`, screenshot + compare tools | Claude vision ground truth; Level Designer + Art Director roles |
| 4 | `studio/review.py`, `loop.py` | Daily standup / retro writer; recurring runner |
| 5 | Worker role + `studio-execute` CLI | Engine-modify path with snapshot before, vision verify after |
| 6 | `studio/config.py`, RehearsalLLM, allowlist sandbox | Threshold templating, dry-run mode, security hardening |
| 7 | `studio/dispatch.py`, `studio-autopilot` CLI | Auto-routing tasks to roles; closes the autonomy circuit |
| 8 | `studio/runner.py:OllamaClient` | Local model provider; Gemma 4 / Qwen 2.5 driven studios |
| 9 | `docs/STUDIO.md`, `studio-loop --with-dispatch` | Documentation + review-then-dispatch in one cadence |
| 10a | `studio/config.py:load_thresholds`, `state.thresholds` | Project-level threshold override via `studio/config.json` |
| 10b | `studio_visual_regression_check`, Pillow MAD diff | Cheap local pre-filter before vision compare |
| 11 | `studio/diagnostics.py`, `studio-doctor` CLI | One-command health check across provider, Ollama, Pillow, disk, Unity |
| 12 | `studio/archive.py`, `studio-archive` CLI | Auto-archival of old done/rejected tasks into per-year files |
| 13 | `LoopRunner.archiver_every`, `--auto-archive-every-passes` | Recurring loop runs auto-archive every Nth pass (hands-off maintenance) |
| 14 | `query_archive`, `studio-history` CLI, `studio_query_archive` tool | Filter + browse archived history (year, role, status, date range, search) |
| 15 | `query_decisions`, `studio-decisions` CLI, `studio_query_decisions` tool | Filter + browse decisions.jsonl (author_role, status, date range, search) |
| 16 | `milestones.py`, `studio-milestones` + `studio-tasks` CLIs, `studio_milestone_progress` tool | Computed milestone completion (counts active + archived); filtered backlog browser |
| 17 | Producer milestone-aware prompt + `_check_stale_in_progress` | Standup cites real % per in_progress milestone; doctor warns on >7d stuck tasks |
| 18 | `ratify_decision`, `latest_decisions`, `find_decision`, `--accept`/`--reject`/`--supersede`, id prefix matching | Critic can accept/reject/supersede decisions; ids accept unique prefixes everywhere |
| 19 | `studio/export.py`, `studio-export` CLI | Single-file JSON snapshot for backup / PR review / migration |

### File layout

A `studio-init` plants this under your project:

```text
studio/
  gdd.md             - Game Design Document (one-page truth)
  art_bible.md       - Style, palette, references
  sprint_current.md  - This week's plan (Producer rewrites)
  backlog.json       - Tasks: id, title, role, status, ...
  milestones.json    - Sprint targets, success criteria
  decisions.jsonl    - Append-only design history
  refs/              - You drop reference images here
  reviews/<date>.md  - Producer's daily standup + retro
  qa/
    screenshots/     - Captured Unity SceneView frames
    diffs/           - (reserved for future Pillow pixel-diff)
    regression.jsonl - Time series of vision_compare scores + perf
  memory/            - (reserved for future memory_system attach)
  .gitignore         - excludes qa/screenshots, qa/diffs, memory/
```

### Data flow per task

```text
  studio-review (Producer)
       |
       | studio_add_task(role="level_designer", title="Place tree...")
       v
  backlog.json
       |
       | studio-autopilot picks oldest PENDING
       v
  Dispatcher.dispatch_one
       |
       | DISPATCH_MAP[level_designer] = "worker"
       v
  Worker (system prompt: snapshot first, place, verify)
       |
       | unity_create_scene_snapshot
       | unity_create_primitive
       | unity_set_position
       | unity_save_scene
       | studio_capture_screenshot
       | studio_compare_to_reference (-> qa/regression.jsonl)
       | studio_update_task_status("done" or "blocked")
       v
  Final task status persisted; Dispatcher coerces stale in_progress
  to "review" if Worker forgot to update.
```

## Roles

Six roles, each with its own system prompt, tool whitelist, and
default behaviour. The `_validate_role_tools()` import-time check
ensures every `studio_*` reference is real; engine references are
runtime-validated.

| Role | Owns | Reads | Writes |
|---|---|---|---|
| **producer** | Backlog, sprint plan | summary, gdd, art bible, sprint, tasks, decisions, milestones, recent commits, recent regressions | sprint, new tasks |
| **designer** | GDD content | summary, gdd, decisions | gdd, decision proposals, own task status |
| **critic** | Consistency | summary, gdd, art bible, decisions, tasks | new review tasks, decision proposals, own task status |
| **art_director** | Art bible, palette | summary, art bible, refs, screenshots | art bible, decision proposals, palette tasks, own task status |
| **level_designer** | Layout audits | summary, gdd, art bible, refs, screenshots | placement tasks (filed for Worker), decisions |
| **worker** | Engine changes | gdd, art bible, refs, scene catalog | scene snapshot, primitives, transforms, materials, screenshots, vision compare, own task status |

Role allowlists live in `unitytools/studio/roles.py`. To add a role:
write its system prompt, list its `allowed_tools`, register it in the
`_ROLES` dict.

### Capability flags

Two derived properties drive the Dispatcher's prerequisite check:

- `role.needs_engine` -> True if any tool is `unity_*` / `unreal_*` /
  `blender_*` or `studio_capture_screenshot`. Dispatcher skips when
  no Unity bridge is connected.
- `role.needs_vision` -> True if `studio_compare_to_reference` is in
  the allowlist. Vision is soft: missing => the tool itself returns
  an error and the role can still run.

## CLI commands

All commands take `--project` (default `.`).

### `studio-init`

Scaffold `studio/` for a project. Idempotent for JSON state, opt-in
for starter docs:

```sh
unitytools studio-init --project .
unitytools studio-init --project . --force   # rewrite gdd.md / art_bible.md
```

### `studio-doctor`

One-command health check across the whole studio. Runs in 1-2 seconds
because every probe is bounded:

```sh
unitytools studio-doctor
# Studio Doctor
#   [OK]   Studio root        /path/to/studio
#   [OK]   Provider           ollama, model gemma4:latest
#   [OK]   Ollama API         reachable, target installed (6 total)
#   [WARN] Anthropic key      absent -- compare-tool unavailable
#   [OK]   Pillow             11.3.0
#   [OK]   Tool registry      132 total, 21 studio_*
#   [OK]   Disk state         all canonical files present
#   [OK]   Config overrides   no config.json (using defaults)
#   [WAIT] Unity bridge       Editor not connected -- engine tasks will skip
#   [WARN] Last review        no reviews yet
#   [OK]   Backlog            0 tasks (fresh project)
#
# Summary: ok=8, warn=2, wait=1
```

Exit code: 1 only when at least one check is `[FAIL]`. Warnings and
waits are 0-exit so cron / CI does not flap on transient
editor-not-connected states.

### `studio-export`

Bundle the whole studio (docs, tasks, decisions, milestones+progress,
archive summary, thresholds, regression tail) into one JSON document.
Useful for backup, PR review (a reviewer sees the whole studio in one
file), migration between machines, or piping into jq.

```sh
unitytools studio-export                                # stdout, pretty
unitytools studio-export -o snapshot.json
unitytools studio-export --compact                      # one-line JSON
unitytools studio-export --include-doctor               # embed health checks
unitytools studio-export --include-history 50           # last 50 archived tasks
unitytools studio-export --include-reviews 7            # last 7 review .md verbatim
unitytools studio-export -o - | jq '.milestones[0]'
```

Schema (top-level keys):

```text
schema_version              integer (currently 1)
exported_at / *_iso         timestamps
project_root, studio_root   paths
docs                        {gdd, art_bible, sprint_current} -> full markdown
tasks                       active backlog (not archive)
decisions                   latest-per-id (current state)
milestones                  each entry has computed progress block
archive_summary             {total, years[], files[]}
thresholds, thresholds_default   effective vs source defaults
review_files                filenames only
qa_regression_tail          last N rows of qa/regression.jsonl
                            (controlled by --include-regression)
```

Optional sections (off by default):

```text
doctor             list of Check dicts (requires --include-doctor)
archive_recent     last N archived tasks (requires --include-history N)
reviews            {filename: markdown body} (--include-reviews N)
```

Pure read; never mutates state. Crash-proof against missing files
(each section degrades to a sensible empty default).

### `studio-tasks`

Active backlog browser. Same filter shape as `studio-history` /
`studio-decisions` but operates on the live `backlog.json` (not the
archive).

```sh
unitytools studio-tasks                                  # newest 50
unitytools studio-tasks --status pending --role worker
unitytools studio-tasks --milestone m1
unitytools studio-tasks --search "pine tree"
unitytools studio-tasks --status blocked --json | jq .
```

### `studio-milestones`

Computed completion progress per milestone. Counts BOTH active
backlog tasks AND archived done tasks, so a freshly archived task
does not disappear from the percentage.

```sh
unitytools studio-milestones                       # every milestone
unitytools studio-milestones --milestone-id m1     # one deep dive
unitytools studio-milestones --json | jq .
```

Sample output:

```text
Milestones (2)
  m1abcdef    Vertical slice   [in_progress]   60.0%  3/5 tasks done, target 2026-06-01
               by_status: blocked=1, done=3, pending=1
               success criteria: 4
  m2zzzzzz    Polish pass      [planning]       0.0%  0/0 tasks done
```

Exposed to Producer + Critic as `studio_milestone_progress(milestone_id)`
so a standup can cite real numbers instead of vibes.

### `studio-decisions`

Browse and ratify the decisions log. Read mode is the same filter
shape as `studio-history` / `studio-tasks`.

```sh
unitytools studio-decisions                                # last 50, newest first
unitytools studio-decisions --status proposed              # what's pending review
unitytools studio-decisions --role designer --status accepted
unitytools studio-decisions --search "palette"
unitytools studio-decisions --show-summary                 # add totals line
unitytools studio-decisions --json | jq .

# Ratify (Critic's job; mutually exclusive)
unitytools studio-decisions --accept 4f93        # exact id or unique prefix
unitytools studio-decisions --reject 152e
unitytools studio-decisions --supersede 4f93 --by abcd
```

Ratification is append-only: a new row with the same id and updated
status goes into `decisions.jsonl`. The original proposal stays for
audit; all readers (`latest_decisions`, `query_decisions`,
`studio_list_decisions`, the CLI listing) dedupe by id and show the
current state. Use `state.load_decisions()` to see the full history.

Exposed to Producer, Critic, and Designer via `studio_query_decisions`
so an agent can answer "did anyone already propose this?" before
filing a duplicate. Ratification (`studio_ratify_decision`) is in the
Critic's allowlist ONLY -- per the Producer prompt, the Producer asks
the Critic to ratify rather than doing it itself.

### ID prefix matching

`studio-execute --task-id` and `studio-decisions --accept/--reject/--supersede`
all accept a unique id prefix instead of the full 12-char id. Examples:

```sh
unitytools studio-execute --task-id 4d84            # full or prefix
unitytools studio-decisions --accept 4f93           # unique 4-char prefix
```

Ambiguous prefixes resolve to no match (lists candidates) instead of
silently picking one.

### `studio-history`

Read-only browser over the archive. Filters compose; output is
human-readable by default, `--json` for piping into other tools.

```sh
unitytools studio-history                                  # last 50, newest first
unitytools studio-history --year 2025 --role designer
unitytools studio-history --status rejected --limit 10
unitytools studio-history --since 2025-01-01 --until 2025-06-30
unitytools studio-history --search "palette"
unitytools studio-history --year 2025 --json | jq .
```

The same query is also exposed to the Producer and the Critic via the
`studio_query_archive` tool, so a standup can ask "did we already do
something like this?" before opening a duplicate task.

### `studio-archive`

Move stale `done` / `rejected` tasks out of `backlog.json` into
per-year files under `studio/archive/<YYYY>.json`. Working set stays
hot, history stays browsable.

```sh
unitytools studio-archive --dry-run             # preview
unitytools studio-archive                       # default: > 30 days old
unitytools studio-archive --older-than-days 90
unitytools studio-archive --statuses rejected   # narrow filter
```

Idempotent: re-running merges by id, newest copy wins. `studio-doctor`
warns when at least 20 archivable tasks pile up so you remember to
run this.

```python
# Browse history programmatically
from unitytools.studio import load_archived_tasks
all_history = load_archived_tasks(state)
just_2025 = load_archived_tasks(state, year=2025)
```

### `studio-status`

Counts and doc presence snapshot:

```sh
unitytools studio-status
# Studio /Users/me/my-game/studio
#   Docs: GDD [OK], Art Bible [OK], Sprint [OK]
#   Tasks:      8
#     - pending      5
#     - done         3
#   Milestones: 1
#   Decisions:  4
```

### `studio-run`

Run one role with a brief:

```sh
# Default brief, real Ollama (Gemma 4)
unitytools studio-run --role designer

# Custom brief, override model
unitytools studio-run --role critic --brief "Audit the GDD pillars" \
                     --model qwen2.5:14b-instruct

# Dry-run, no API calls (only doc-only roles)
unitytools studio-run --role designer --dry-run

# Cap iterations for tight runs
unitytools studio-run --role designer --max-iterations 4
```

### `studio-review`

Producer pass that writes today's `studio/reviews/<date>.md`:

```sh
unitytools studio-review --phase morning   # standup
unitytools studio-review --phase evening   # retro
unitytools studio-review --phase adhoc --extra "Sprint demo on Friday"
unitytools studio-review --dry-run         # API-free
```

The review file accumulates same-day passes (morning header + evening
header in one file).

### `studio-loop`

Recurring Producer reviews. Useful for cron or persistent shells:

```sh
# One pass and exit (recommended for cron)
unitytools studio-loop --once

# Every 12 hours, until killed (Ctrl+C in 1s)
unitytools studio-loop --interval-hours 12

# Stop after N passes
unitytools studio-loop --interval-hours 24 --max-passes 7

# Self-driving: review + dispatch + weekly auto-archive
unitytools studio-loop --interval-hours 24 --with-dispatch \
                      --auto-archive-every-passes 7 --auto-archive-age-days 30
```

Options:
- `--with-dispatch` runs the autopilot dispatcher after each review.
- `--auto-archive-every-passes N` (default 0 = off) runs auto-archive
  on every Nth pass. With `--interval-hours 24` and `N=7` that's
  weekly archive without manual intervention.
- `--auto-archive-age-days` overrides the 30d default for the loop's
  archive calls.

### `studio-execute`

Pick a single backlog task and run the Worker:

```sh
unitytools studio-execute --task-id 4d8461106c38

# Re-run a task that's already done/rejected
unitytools studio-execute --task-id <id> --force

# Override model for tricky tasks
unitytools studio-execute --task-id <id> --model qwen2.5:14b-instruct
```

Lifecycle: pending|review -> in_progress -> the Worker flips to "done"
or "blocked"; if it forgets, the runner coerces "review".

### `studio-autopilot`

Walk the backlog and dispatch each pending task to the right role:

```sh
unitytools studio-autopilot --max-tasks 5
unitytools studio-autopilot --only-role designer       # filter by source role
unitytools studio-autopilot --dry-run                  # rehearsal
unitytools studio-autopilot --model gemma4:latest      # override per role
```

Output stream: `[OK]` / `[BLOCK]` / `[REVIEW]` / `[SKIP]` / `[ERR]` per
task, then a counts summary.

## Local model setup (Ollama)

Studio runs against any tool-calling-capable Ollama model. Tested:

```sh
ollama pull gemma4:latest         # 8B, fast, good for doc roles
ollama pull qwen2.5:14b-instruct  # 14B, best tool-calling reliability
ollama pull qwen2.5:7b-instruct   # 7B, fallback for low-VRAM rigs
ollama pull llama3.1:8b           # alternative
```

In `.env`:

```sh
UNITYTOOLS_PROVIDER=ollama
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=gemma4:latest
```

Per-role overrides via `--model`:

```sh
# Heavy planner on Qwen 14B, lighter writer on Gemma 4
unitytools studio-run --role producer --model qwen2.5:14b-instruct
unitytools studio-run --role designer --model gemma4:latest
```

### When Ollama can't tool-call cleanly

Some local models occasionally print tool calls as JSON in the
assistant message instead of using their structured tool-call channel.
The OllamaClient has a text-fallback parser that recovers them, gated
by the registered tool name set so it cannot dispatch hallucinated
tool names. If you see roles loop without ever calling tools, you
likely need a bigger or more tool-trained model.

### Vision compare needs Anthropic

`studio_compare_to_reference` calls Claude vision (Sonnet/Opus). Doc
roles work fully on Ollama; engine roles that compare against
reference images need `ANTHROPIC_API_KEY`. Without it, the compare
tool returns a clean error and the rest of the Worker flow continues.

### Cheap visual regression (Pillow, no LLM)

`studio_visual_regression_check(reference_path, candidate_path)`
returns a 0..1 similarity, mean absolute pixel difference, and
per-channel color drift using `PIL.ImageChops.difference`. No LLM
call, no API key, no network. Use as a cheap pre-filter:

```text
1. studio_capture_screenshot           (real Unity capture)
2. studio_visual_regression_check      (cheap local diff vs last frame)
3. if similarity > 0.95: skip vision compare  (scene unchanged)
4. else: studio_compare_to_reference   (call Claude vision once)
```

The tool also appends a `pixel_diff` row to `qa/regression.jsonl`
alongside `vision_compare` rows so a producer's
`studio_recent_regressions` view shows both signals. Available to the
LEVEL_DESIGNER, ART_DIRECTOR, and WORKER roles.

## Project state on disk

Everything is human-readable. You can `git add studio/` and review
diffs over time.

| File | Format | Mutability |
|---|---|---|
| `gdd.md` | Markdown | Designer rewrites with full file |
| `art_bible.md` | Markdown | Art Director rewrites |
| `sprint_current.md` | Markdown | Producer rewrites in evening retro |
| `backlog.json` | JSON | Atomic full-rewrite on every change |
| `milestones.json` | JSON | Same |
| `decisions.jsonl` | JSON-lines | Append-only history |
| `qa/regression.jsonl` | JSON-lines | Append-only QA time series |
| `reviews/<date>.md` | Markdown | Append within same day |

Atomic writes go via `tempfile + os.replace` so a crash mid-write
cannot leave half-written JSON.

## Tuning

### Project-level overrides (studio/config.json)

Drop a `studio/config.json` at the project root to override any subset
of `StudioThresholds`. Unknown keys are ignored with a warning;
malformed JSON falls back to defaults. `studio-doctor` and
`studio-status` both surface what's effective.

```json
{
  "max_tasks_per_producer_run": 8,
  "max_worker_iterations": 16
}
```

The two threshold values templated into role prompts at module-import
time (`worker_block_threshold`, `level_designer_reblock_threshold`)
are exceptions: project overrides apply to code paths that read them,
but do NOT rewrite the prompt text. To change those, edit
`config.py` defaults and reimport, or build custom RoleConfigs.

### Thresholds

`unitytools/studio/config.py:STUDIO_DEFAULTS` has the dials that
matter:

```python
worker_block_threshold:           0.5  # composition_match below this -> Worker blocks task
level_designer_reblock_threshold: 0.6  # below this -> Critic asked via decision
max_tasks_per_producer_run:       5    # cap on new tasks per Producer pass
max_role_iterations:              8    # tool-call cap, reviewer roles
max_worker_iterations:            12   # tool-call cap, Worker
```

These thresholds are templated into the role prompts at module-load
time (`_format()` in `roles.py`), so editing `config.py` changes both
what the LLM sees and any future code-side checks against the same
constants.

### Custom briefs

Default briefs live in `unitytools/cli/entry.py:_default_brief_for`.
The `--brief` flag on `studio-run` overrides; `--extra` on
`studio-review` and `studio-execute` appends extra context to the
default. For project-wide brief overrides, the cleanest path right
now is a wrapper script.

### Custom rehearsal scripts

Dry-run rehearsals live in `unitytools/studio/runner.py:_REHEARSAL_SCRIPTS`.
To add a script for a new role: insert a list of step dicts (each
`{"name": tool_name, "input": {...}}`) plus a final `None` entry
marking the terminating turn. Steps that the role's allowlist excludes
are skipped at runtime, so rehearsal scripts surviving role changes is
a soft contract.

## Troubleshooting

**"No LLM provider configured"**: set `UNITYTOOLS_PROVIDER=ollama`
plus `OLLAMA_MODEL=...`, OR `UNITYTOOLS_PROVIDER=anthropic` plus
`ANTHROPIC_API_KEY=sk-ant-...`. There's no silent default.

**"Ollama not reachable at http://127.0.0.1:11434"**: run
`ollama serve` in another terminal. On Windows the Ollama service
sometimes idles; restarting the Ollama app brings it back.

**"Tool 'X' is not allowed for this role"**: the role's allowlist
sandbox refused a tool the LLM tried to call. Either widen the
allowlist in `roles.py` or rephrase your brief so the role uses tools
it does have.

**Worker says "blocked" with composition_match below 0.5**: the change
made the scene drift further from the reference. Read the diff in
`qa/regression.jsonl`'s last entry, decide whether to refile a smaller
task or update the reference image.

**Engine-bound tasks all "[SKIP] engine bridge not available"**: open
Unity Editor and start the BridgeServer (`Window > UnityTools AI`).
The studio talks to Unity via TCP on port 7777.

**Designer wrote "rehearsal placeholder" into GDD**: you ran
`--dry-run`. That's the canned RehearsalLLM. Re-run without `--dry-run`
once provider is configured.

**`--dry-run` rejected for level_designer / art_director / worker**:
those roles need a real engine to do anything productive. Dry-run is
limited to doc-only roles (producer / designer / critic) by design.

## Project layout cheat sheet

```text
unitytools/studio/
  __init__.py        - public API surface
  paths.py           - StudioPaths (filesystem layout, single source of truth)
  models.py          - Task / Decision / Milestone dataclasses + status enums
  state.py           - StudioState (atomic I/O, summary)
  tools.py           - 20 @tool functions exposed to roles
  roles.py           - 6 RoleConfig instances + _format() prompt templating
  runner.py          - RoleRunner, AnthropicClient, OllamaClient, RehearsalLLM
  vision.py          - VisionClient protocol + AnthropicVisionClient
  review.py          - daily standup / retro writer
  loop.py            - LoopRunner (interval, --once)
  dispatch.py        - Dispatcher (auto-route pending tasks to roles)
  config.py          - StudioThresholds (frozen tunables)
  templates.py       - starter content for studio-init

tests/
  test_studio_state.py        - Phase 1
  test_studio_roles.py        - Phase 2
  test_studio_vision.py       - Phase 3
  test_studio_loop.py         - Phase 4
  test_studio_worker.py       - Phase 5
  test_studio_calibration.py  - Phase 6
  test_studio_autopilot.py    - Phase 7
  test_studio_ollama.py       - Phase 8
```

Every test runs without a network call (Anthropic and Ollama are both
mocked) and without Unity (a FakeUnityBridge stands in).

## A real session: pitch to placement

```sh
# Day 1 morning
$ unitytools studio-init --project .
[OK] Studio initialized at .../studio

# Drop a reference image in studio/refs/level_1_target.png

$ unitytools studio-run --role designer --brief "Pitch a 30-min dungeon crawler"
Provider: ollama, model: gemma4:latest.
  -> studio_read_gdd       <- [OK]
  -> studio_write_gdd      <- [OK]
Done -- iterations=3, tool_calls=2

$ unitytools studio-review --phase morning
[OK] iterations=4, tools=3, stop=end_turn
Wrote .../studio/reviews/2026-05-10.md

# Producer opened: refine pillars (designer), audit scene (level_designer),
# pick palette (art_director).

$ unitytools studio-autopilot --max-tasks 3
  [OK]      bed7... (designer):       Refine GDD pillars
  [SKIP]    7983... (worker):         Audit scene against reference
            -- engine bridge not available (Unity not open)
  [OK]      4d84... (art_director):   Draft palette block

# Open Unity, start the bridge, then re-run autopilot to pick up the
# skipped engine task.
$ unitytools studio-autopilot --only-role level_designer --max-tasks 1
  [OK]      7983... (worker): Audit scene against reference
              -> snapshot, screenshot, compare, place, verify, done

# Day 1 evening
$ unitytools studio-review --phase evening
# Wrote underneath today's morning entry: what shipped, what slipped.
```

## Phase history

For PR readers and future contributors:

- **Phase 1**: state I/O — file layout, dataclasses, atomic writes, CLI
  scaffold (`studio-init`, `studio-status`).
- **Phase 2**: doc-level tools, 3 roles (Producer / Designer / Critic),
  RoleRunner with LLM Protocol; `studio-run`.
- **Phase 3**: vision grounding — Claude vision compare, Unity
  screenshot capture, Level Designer + Art Director roles.
- **Phase 4**: review writer + LoopRunner — `studio-review`,
  `studio-loop`. Producer gains recent_commits / recent_regressions
  inputs.
- **Phase 5**: Worker role + engine-modify path — `studio-execute`,
  task lifecycle (in_progress -> done/blocked/review).
- **Phase 6**: calibration — frozen StudioThresholds, prompt
  templating, allowlist sandbox at execution time, RehearsalLLM
  dry-run, fixed Windows console Unicode crash.
- **Phase 7**: Dispatcher + DISPATCH_MAP — `studio-autopilot`. Roles
  gain capability flags (needs_engine, needs_vision). Designer /
  Critic / Art Director gain `studio_update_task_status` for the
  dispatch lifecycle.
- **Phase 8**: OllamaClient — local-first studio. `make_default_client`
  dispatches by provider. `--model` flag on every command.

Future phases (not yet implemented):

- **Phase 9 (this doc)**: `docs/STUDIO.md`.
- Visual regression baseline using Pillow / imagehash for cheap pixel
  diff between consecutive screenshots.
- Per-project `studio/config.json` to override `StudioThresholds`
  without editing source.
- Producer auto-dispatch loop: `studio-loop --with-dispatch` runs
  review then autopilot in one cadence.
- Multi-worker concurrency with a scene-edit mutex.
- Ollama vision support (Gemma 3 / Qwen 2.5-VL) so studios with no
  Anthropic key can do vision compare too.
