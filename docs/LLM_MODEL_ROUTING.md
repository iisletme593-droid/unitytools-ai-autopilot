# LLM Model Routing (Cloudflare Workers AI)

When `UNITYTOOLS_PROVIDER=cloudflare`, the autopilot picks a **task-specialised model per
turn** instead of using one model for everything. It reads your message, detects the task,
and routes to the most suitable Cloudflare Workers AI model — automatically, and
controllable from chat.

This is a **deterministic, code-derived router** (`unitytools/core/model_router.py`), not a
learning system: it maps task keywords → models. Honest about what it is.

## The catalog (model ids verified on developers.cloudflare.com)

**Live text routing** — the router picks among these per turn:

| task | model | tool-calling | best at |
|------|-------|--------------|---------|
| `reasoning` (default) | `@cf/openai/gpt-oss-120b` | ✅ | reasoning, agentic, planning |
| `general` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | ✅ | all-round instruct, fast (fp8) |
| `coding` | `@cf/qwen/qwen2.5-coder-32b-instruct` | ❌ | code generation / debugging |
| `creative` | `@cf/zai-org/glm-4.7-flash` | ✅ | storytelling, dialogue, multilingual |
| `fast` | `@cf/meta/llama-3.1-8b-instruct-fast` | ❌ | simple / cheap / high-throughput |

**Catalogued but not routed by the text loop** (they need a different API shape — a
dedicated tool would use them):

| task | model | modality |
|------|-------|----------|
| `vision` | `@cf/meta/llama-3.2-11b-vision-instruct` | text + image input |
| `image` | `@cf/black-forest-labs/flux-1-schnell` | text → image (base64) |

## How a model is chosen (in order)

1. **Explicit override from chat** wins — e.g. `coder modeliyle ...`, `use the creative
   model`, `model: reasoning`, or naming a raw `@cf/...` id.
2. If **auto-routing is off** (`CLOUDFLARE_AUTO_ROUTE=0`) → always `CLOUDFLARE_MODEL`.
3. **Tool-requiring turns** (any Unity/Unreal action that needs the tools) → always a
   verified **tool-capable** model (`gpt-oss-120b`), so the tool-loop can never break.
4. Otherwise → the task type is **auto-detected** from the message (coding / creative /
   reasoning / fast / general).

Safety rails: a non-tool override (e.g. "coder") on a tool-requiring turn is upgraded to
the tool-capable default rather than break tool-calling; the live loop never routes to the
`vision`/`image` models (wrong API shape for a chat loop).

## Controlling it from chat

- Force a model: `"coder modeliyle bu fonksiyonu yaz"`, `"use the creative model"`,
  `"hizli model ile ozetle"`.
- The model is fixed for the whole tool-loop of one turn (no mid-turn switching).

## Config

- `CLOUDFLARE_MODEL` — the configured default / the model used when auto-routing is off.
- `CLOUDFLARE_AUTO_ROUTE` — `1` (default) to auto-route, `0/false/off/kapali` to disable.

The router is pure + deterministic and fully unit-tested (`tests/test_model_router.py`),
including the orchestrator wiring and the tool-safety rails.
